# Risk RAG Copilot

A minimal GenAI + Retrieval-Augmented Generation (RAG) prototype inspired by RBC Group Risk Management (GRM) use cases.

## What it does (concept)

- Ingests sample risk/policy-style documents.
- Uses embeddings + vector search to retrieve relevant context.
- Calls an LLM with a governance-focused prompt:
  - answers only from provided context,
  - surfaces citations for each answer,
  - is cautious and audit-friendly.
- Exposes a simple API endpoint (FastAPI) to ask questions.

## Why this exists

This project is a lightweight sandbox to practice:

- Building modular, production-style Python 3.x services.
- Implementing a basic RAG pipeline (ingestion → embeddings → vector store → prompt).
- Thinking about GenAI in regulated environments:
  - traceability,
  - context-only answers,
  - clear separation of components.

It is **not** connected to real RBC systems or real policies; all documents are dummy placeholders for demonstration only.

## Tech stack

- Python 3.x
- FastAPI
- Simple in-memory vector store (can be swapped for FAISS / pgvector / etc.)
- LLM + embeddings via pluggable client (OpenAI / Hugging Face, etc.)

## Usage (high level)

1. Add sample `.txt` documents under `data/`.
2. Run the RAG service (to be implemented) with FastAPI.
3. Query:

```http
GET /ask?question=How do we manage operational risk?