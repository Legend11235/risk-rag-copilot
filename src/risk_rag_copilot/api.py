from pathlib import Path
import re, time

from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from pydantic import BaseModel

from .rag_pipeline import answer_question, rebuild_index, index_stats
from .pdf_utils import extract_text_from_pdf
from .config import DATA_DIR

app = FastAPI(title="Risk RAG Copilot")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500","http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnswerResponse(BaseModel):
    answer: str
    sources: list

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stats")
def stats():
    return index_stats()

@app.post("/rebuild")
def rebuild():
    return rebuild_index()

@app.get("/ask", response_model=AnswerResponse)
def ask(question: str = Query(..., description="Risk-related question")):
    return AnswerResponse(**answer_question(question))

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    data = await file.read()
    text = extract_text_from_pdf(data)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", (file.filename or "document"))
    out_path = Path(DATA_DIR) / f"{int(time.time())}_{safe}.txt"
    out_path.write_text(text, encoding="utf-8")

    stats = rebuild_index()  # hot reindex so it’s queryable immediately
    return {"saved": out_path.name, **stats}