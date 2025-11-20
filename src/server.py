import os
from typing import Annotated
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

# Your existing router
from .sentiment_bot import route_by_sentiment

load_dotenv()

# --- Configuration and Secrets ---

# Check for API keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GOOGLE_API_KEY or not GROQ_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY or GROQ_API_KEY in .env")

# --- Authentication Configuration and Helpers ---

# Basic Auth Scheme Initialization
security = HTTPBasic()

# Mock User Database (For testing. Replace this with a secure DB in production!)
# Key: username, Value: plain text password (Should be hashed in a real app)
USERS_DB = {
    "testuser": "password123"
}

def get_current_basic_user(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """
    Dependency to check HTTP Basic credentials.
    Raises HTTPException 401 if credentials do not match mock DB.
    """
    username = credentials.username
    password = credentials.password
    
    # Check credentials (In a real application, you must use a hashing library like bcrypt)
    expected_password = USERS_DB.get(username)
    
    if not expected_password or password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return username # Return the validated username

# --- FastAPI App Setup ---

app = FastAPI(title="Sentiment Chat API (Basic Auth)")

# Adjust CORS settings
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [s.strip() for s in ALLOWED_ORIGINS_STR.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# --- New Basic Auth Test Endpoint ---

@app.get("/users/me")
def read_current_user(current_user: Annotated[str, Depends(get_current_basic_user)]):
    """
    Test endpoint secured by HTTP Basic Authentication.
    Returns the username if authentication succeeds.
    """
    return {"username": current_user}

# --- Secured Chat Endpoint ---

@app.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    current_user: Annotated[str, Depends(get_current_basic_user)] # SECURE THIS ENDPOINT
):
    """
    Chat endpoint is now secured. Only requests with valid Basic Auth
    credentials (username/password) can access this resource.
    """
    print(f"Authenticated user: {current_user}") # Log user for verification
    
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    try:
        reply = route_by_sentiment(msg)
        return ChatResponse(reply=reply)
    except Exception as e:
        # Log error in real life
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
 
# --- Static File Serving ---

app.mount(
    "/",
    StaticFiles(directory="chat_ui", html=True),
    name="static"
)