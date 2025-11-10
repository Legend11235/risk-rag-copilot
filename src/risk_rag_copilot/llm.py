import os
import numpy as np
from dotenv import dotenv_values, load_dotenv
from openai import OpenAI
from .config import LLM_MODEL, EMBEDDING_MODEL, DOTENV_PATH

# Load .env and read key
load_dotenv(DOTENV_PATH, override=False)
api_key = os.getenv("OPENAI_API_KEY") or dotenv_values(DOTENV_PATH).get("OPENAI_API_KEY")
_client = OpenAI(api_key=api_key)

# Tight system guardrails + correct citation instruction
SYSTEM_MSG = (
    "You are a cautious GRM assistant. Use ONLY the provided Context.\n"
    "Cite using the exact numbered tags from the Context, e.g., [Source 1], [Source 2].\n"
    "Never write [Source i]. If the Context is insufficient, answer: 'Insufficient context to answer.'"
)

def get_embedding(text: str) -> np.ndarray:
    """Return an L2-normalized embedding vector from OpenAI."""
    resp = _client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    v = np.array(resp.data[0].embedding, dtype=float)
    v /= (np.linalg.norm(v) + 1e-10)
    return v

def call_llm(prompt: str):
    """
    Conservative chat completion (regulated context).
    Returns: (answer_text: str, usage: dict)
    """
    model = os.getenv("LLM_MODEL", LLM_MODEL)
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        top_p=1,
    )
    text = resp.choices[0].message.content.strip()
    usage = {
        "model": model,
        "prompt_tokens": int(getattr(getattr(resp, "usage", None), "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(getattr(resp, "usage", None), "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0),
    }
    return text, usage