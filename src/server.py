# server.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Your existing router
from sentiment_bot import route_by_sentiment

load_dotenv()

# Optional: sanity check for keys you already rely on
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GOOGLE_API_KEY or not GROQ_API_KEY:
    # You can keep this strict or just warn. I'll keep strict since your code needs them.
    raise RuntimeError("Missing GOOGLE_API_KEY or GROQ_API_KEY in .env")

app = FastAPI(title="Sentiment Chat API")

# Adjust this for your frontend host/port in dev/prod
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,     # e.g., ["http://localhost:5500", "http://127.0.0.1:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        reply = route_by_sentiment(msg)
        return ChatResponse(reply=reply)
    except Exception as e:
        # Log in real life
        raise HTTPException(status_code=500, detail=str(e))
