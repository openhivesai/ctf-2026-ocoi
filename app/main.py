# public/app/src/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import uuid
from rag import answer

app = FastAPI(title="IA RAG CTF – Sobriété Numérique")


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/start")
def start():
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


@app.post("/chat")
def chat(req: ChatRequest):
    return answer(req.message)