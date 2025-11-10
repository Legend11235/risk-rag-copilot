# src/risk_rag_copilot/prompts.py
from typing import List

def build_prompt(question: str, retrieved: List[tuple]) -> str:
    lines = []
    for i, item in enumerate(retrieved, start=1):
        if len(item) == 3:
            txt, _sim, fname = item
            lines.append(f"[Source {i}] ({fname}) {txt}")
        else:
            txt, _sim = item
            lines.append(f"[Source {i}] {txt}")
    ctx = "\n\n".join(lines)

    return (
        "You are an RBC Group Risk Management assistant. Use ONLY the Context below.\n"
        "If the Context is insufficient, answer exactly: 'Insufficient context to answer.'\n"
        "Rules:\n"
        " - Cite using the exact numbered tags from Context (e.g., [Source 1], [Source 2]).\n"
        " - Include a [Source N] tag for each factual claim (at least once per bullet/paragraph).\n"
        " - Do not invent sources or numbers; only use those shown in Context.\n"
        " - Be concise; use bullets when listing items.\n\n"
        f"Context:\n{ctx}\n\nQuestion: {question}\nAnswer:"
    )