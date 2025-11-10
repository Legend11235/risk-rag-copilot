from typing import Dict, Any, List, Tuple
from pathlib import Path
import hashlib, json, os, time
from threading import Lock

from .ingestion import load_documents, chunk_text
from .vectorstore import InMemoryVectorStore
from .prompts import build_prompt
from .config import DATA_DIR, TOP_K, SIM_THRESHOLD, ENFORCE_CITATIONS, LOG_DIR
from .llm import call_llm

# ---- process-global index state ----
_store: InMemoryVectorStore | None = None
_built = False
_index_lock = Lock()

def _build_store() -> None:
    """(Re)build the in-memory vector store from DATA_DIR."""
    global _store, _built
    docs = load_documents(DATA_DIR)
    chunks: List[str] = []
    for d in docs:
        chunks.extend(chunk_text(d))
    _store = InMemoryVectorStore(chunks)
    _built = True

def _has_citation(text: str) -> bool:
    return "[Source " in (text or "")

def _log_event(payload: Dict[str, Any]) -> None:
    """Write one JSON object per line to logs/events.jsonl (best-effort)."""
    try:
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        with open(Path(LOG_DIR) / "events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # never break the API on logging errors
        pass

def answer_question(question: str) -> Dict[str, Any]:
    """Main RAG flow with guardrails + audit logging."""
    global _built, _store
    t0 = time.time()

    # Lazy build under a lock (first request only)
    if not _built:
        with _index_lock:
            if not _built:
                _build_store()

    if _store is None:
        # extremely defensive fallback
        ans = "Insufficient context to answer."
        return {"answer": ans, "sources": []}

    # 1) Retrieve
    retrieved: List[Tuple[str, float]] = _store.search(question, k=TOP_K)
    sources = [
        {"id": i + 1, "similarity": float(s), "snippet": txt[:200].replace("\n", " ")}
        for i, (txt, s) in enumerate(retrieved)
    ]

    # 2) Threshold refusal (no weakly-supported answers)
    max_sim = max((s for _txt, s in retrieved), default=0.0)
    if not retrieved or max_sim < SIM_THRESHOLD:
        ans = "Insufficient context to answer."
        _log_event({
            "ts": time.time(),
            "question": question,
            "max_sim": max_sim,
            "decision": "refuse_threshold",
            "topk": sources,
            "latency_ms": round((time.time() - t0) * 1000, 1),
        })
        return {"answer": ans, "sources": sources}

    # 3) Build context-only prompt and call LLM
    triplets = [(txt, s, "in-memory") for (txt, s) in retrieved]  # filename placeholder
    user_msg = build_prompt(question, triplets)
    prompt_hash = hashlib.sha256(user_msg.encode("utf-8")).hexdigest()[:16]

    try:
        ans, usage = call_llm(user_msg)
        decision = "answer"
        # 4) Enforce citation presence
        if ans.strip() != "Insufficient context to answer." and ENFORCE_CITATIONS and not _has_citation(ans):
            ans = "Insufficient context to answer."
            decision = "refuse_no_citation"
    except Exception as e:
        # Any provider/runtime error becomes a governed refusal, logged for audit
        ans = "Insufficient context to answer."
        decision = "refuse_llm_error"
        usage = {"error": str(e)}

    # 5) Audit log
    _log_event({
        "ts": time.time(),
        "question": question,
        "max_sim": max_sim,
        "decision": decision,
        "topk": sources,
        "prompt_hash": prompt_hash,
        "usage": usage,
        "latency_ms": round((time.time() - t0) * 1000, 1),
    })

    return {"answer": ans, "sources": sources}

# ---- Hot rebuild + stats ----

def rebuild_index() -> Dict[str, Any]:
    """Rescan data/, rechunk, re-embed, rebuild index (thread-safe)."""
    t0 = time.time()
    with _index_lock:
        _build_store()
        n_chunks = len(getattr(_store, "texts", [])) if _store else 0
    return {
        "status": "rebuilt",
        "chunks": n_chunks,
        "latency_ms": round((time.time() - t0) * 1000, 1),
    }

def index_stats() -> Dict[str, Any]:
    """Basic health view for demos/ops."""
    if not _built or _store is None:
        return {"built": False, "chunks": 0}
    return {
        "built": True,
        "chunks": len(getattr(_store, "texts", [])),
    }