"""
GFC Financial AI Chatbot - FastAPI backend
Run with: venv/Scripts/uvicorn.exe app.main:app --reload
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel

from app.data_loader import load_data
from app.rag import ask_chatbot, build_chunks

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

load_dotenv()

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found. Check your .env file.")

    state["client"] = genai.Client(api_key=api_key)

    raw, ratios = load_data()
    state["chunks"] = build_chunks(raw, ratios)

    print(f"Startup complete — {len(state['chunks'])} chunks loaded.")
    yield
    state.clear()


app = FastAPI(
    title="GFC Financial AI Chatbot",
    description="RAG-powered Q&A over Apple, Microsoft, and Tesla 10-K filings (FY2023-FY2025).",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local dev; tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HistoryEntry(BaseModel):
    role: str   # "user" or "bot"
    text: str


class AskRequest(BaseModel):
    question: str
    history: list[HistoryEntry] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Which company had the highest net margin in FY2025?",
                "history": []
            }
        }
    }


class AskResponse(BaseModel):
    answer: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["utility"])
def health():
    """Check the API is up and chunks are loaded."""
    return {
        "status": "ok",
        "chunks_loaded": len(state.get("chunks", [])),
    }


@app.post("/ask", response_model=AskResponse, tags=["rag"])
def ask(request: AskRequest):
    """
    Ask a question about Apple, Microsoft, or Tesla financials (FY2023-FY2025).
    Optionally pass conversation history for context-aware follow-up answers.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = [h.model_dump() for h in request.history] if request.history else None

    try:
        answer = ask_chatbot(
            user_question=question,
            chunks=state["chunks"],
            client=state["client"],
            history=history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AskResponse(answer=answer)


# Serve the frontend at / — must be mounted AFTER all API routes
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
