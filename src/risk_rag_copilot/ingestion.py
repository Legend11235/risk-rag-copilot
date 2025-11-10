from pathlib import Path
from typing import List, Optional
import re
from .config import CHUNK_TOKENS, CHUNK_OVERLAP_TOKENS

# --- token length helper (tiktoken if available, else fallback) ---
try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def _toklen(s: str) -> int:
        return len(_enc.encode(s))
except Exception:
    _enc = None
    def _toklen(s: str) -> int:
        # rough fallback: ~0.75 words per token
        words = len(s.split())
        return max(1, int(round(words / 0.75)))

# split on sentence/paragraph-ish boundaries
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+|\n{2,}')

def load_documents(data_dir: str) -> List[str]:
    """
    Load plain-text documents from `data_dir`. We index *.txt files.
    (PDFs should be uploaded via /upload_pdf, which writes a matching .txt.)
    Returns a list of raw document strings.
    """
    p = Path(data_dir)
    if not p.exists():
        return []
    docs: List[str] = []
    for fp in sorted(p.glob("*.txt")):
        try:
            docs.append(fp.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            # skip unreadable files
            continue
    return docs

def chunk_text(text: str,
               target_tokens: Optional[int] = None,
               overlap_tokens: Optional[int] = None) -> List[str]:
    """
    Sentence-aware, token-budgeted chunking with overlap.

    1) Split into sentences/paragraphs.
    2) Greedily pack sentences until ~target_tokens.
    3) Emit chunk; start next chunk by carrying ~overlap_tokens of the tail.
    """
    if not text or not text.strip():
        return []

    T = target_tokens or CHUNK_TOKENS
    O = overlap_tokens or CHUNK_OVERLAP_TOKENS
    sents = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]

    chunks: List[str] = []
    cur: List[str] = []
    cur_tok = 0

    def _emit():
        nonlocal cur, cur_tok
        if not cur:
            return
        chunk = " ".join(cur).strip()
        if chunk:
            chunks.append(chunk)
        # prepare overlap tail
        if O > 0:
            if _enc:
                ids = _enc.encode(chunk)
                tail_ids = ids[-O:]
                cur = [_enc.decode(tail_ids)]
            else:
                words = chunk.split()
                tail_words = max(1, int(round(O * 0.75)))
                cur = [" ".join(words[-tail_words:])]
        else:
            cur = []
        cur_tok = _toklen(" ".join(cur)) if cur else 0

    for s in sents:
        s_tok = _toklen(s)
        if cur_tok + s_tok <= T or not cur:
            cur.append(s)
            cur_tok += s_tok
        else:
            _emit()
            # now add the sentence; if oversized, hard-wrap by words
            if _toklen(s) >= T:
                words = s.split()
                buf: List[str] = []
                buf_tok = 0
                for w in words:
                    w_tok = _toklen(w)
                    if buf_tok + w_tok > T and buf:
                        cur.append(" ".join(buf))
                        _emit()
                        buf, buf_tok = [], 0
                    buf.append(w)
                    buf_tok += w_tok
                if buf:
                    cur.append(" ".join(buf))
                    cur_tok = _toklen(" ".join(cur))
            else:
                cur.append(s)
                cur_tok += _toklen(s)

    if cur:
        _emit()
    return chunks
