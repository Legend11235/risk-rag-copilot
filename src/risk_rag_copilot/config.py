import os
from pathlib import Path
from dotenv import load_dotenv

# ---- Paths & .env ----
BASE_DIR = Path(__file__).resolve().parents[2]   # repo root
DOTENV_PATH = BASE_DIR / ".env"
load_dotenv(DOTENV_PATH, override=False)

# ---- Data & logs ----
DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
TOP_K = int(os.getenv("TOP_K", "5"))

# ---- Models ----
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ---- Chunking (tokens, not characters) ----
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "160"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "32"))

# ---- Retrieval guardrails ----
SIM_THRESHOLD = float(os.getenv("SIM_THRESHOLD", "0.35"))   # refuse if max similarity < this
ENFORCE_CITATIONS = os.getenv("ENFORCE_CITATIONS", "1") == "1"

# ---- Logging ----
LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))
