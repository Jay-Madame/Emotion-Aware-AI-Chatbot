# server.py
import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# Import for Basic Auth
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
import secrets # Used for secure string comparison

# Your existing router
from .sentiment_bot import route_by_sentiment

load_dotenv()

# --- CONFIGURATION & SANITY CHECK ---

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 1. Load Auth Credentials
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")

if not GOOGLE_API_KEY or not GROQ_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY or GROQ_API_KEY in .env")

# 2. Enforce Auth Credentials
if not AUTH_USERNAME or not AUTH_PASSWORD:
    raise RuntimeError("Missing AUTH_USERNAME or AUTH_PASSWORD in .env. Basic Auth is required.")


app = FastAPI(title="Sentiment Chat API")

# Setup Basic Auth mechanism
security = HTTPBasic()

# Adjust this for your frontend host/port in dev/prod
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [s.strip() for s in ALLOWED_ORIGINS_STR.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# 3. Dependency function to check credentials
def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    # Use secrets.compare_digest for constant-time comparison to prevent timing attacks
    is_username_correct = secrets.compare_digest(credentials.username, AUTH_USERNAME)
    is_password_correct = secrets.compare_digest(credentials.password, AUTH_PASSWORD)

    if not (is_username_correct and is_password_correct):
        # Raise 401 Unauthorized, prompting the client to re-send auth headers
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    # If successful, the dependency returns the credentials object, 
    # but we don't need to use it in the endpoint function, just the check is enough.
    return True 

# 4. Apply the dependency to the /chat endpoint
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, authenticated: bool = Depends(authenticate_user)):
    # The 'authenticated' variable will be True if credentials passed the check, 
    # otherwise, HTTPException is raised before this code runs.
    
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        reply = route_by_sentiment(msg)
        return ChatResponse(reply=reply)
    except Exception as e:
        # Log in real life
        raise HTTPException(status_code=500, detail=str(e))
 
app.mount(
    "/",
    StaticFiles(directory="chat_ui", html=True),
    name="static"
)