# src/server.py
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .sentiment_bot import route_by_sentiment
from .database import get_db, init_db, save_chat_message, get_user_by_id
from .auth import (
    authenticate_user,
    register_user,
    verify_user_email,
    request_password_reset,
    reset_password,
    create_access_token,
    create_verification_token,
    send_verification_email
)

load_dotenv()

app = FastAPI(title="Knight Bot Counseling API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Server started successfully")

# ============ REQUEST/RESPONSE MODELS ============

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    email: str

class VerifyEmailRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ChatHistoryMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    user_id: int
    chat_history: Optional[List[ChatHistoryMessage]] = []

class ChatResponse(BaseModel):
    reply: str

class ChatHistoryResponse(BaseModel):
    messages: List[dict]

class MessageResponse(BaseModel):
    message: str

# ============ AUTHENTICATION ENDPOINTS ============

@app.post("/auth/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and send verification email"""
    try:
        user = register_user(db, req.username, req.email, req.password)
        return MessageResponse(
            message=f"Registration successful! Please check {req.email} for verification link."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/auth/verify-email", response_model=MessageResponse)
def verify_email(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify user's email with token from email link"""
    try:
        verify_user_email(db, req.token)
        return MessageResponse(message="Email verified successfully! You can now log in.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login with username and password"""
    try:
        user = authenticate_user(db, req.username, req.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            email=user.email
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset - sends email with reset link"""
    try:
        request_password_reset(db, req.email)
        return MessageResponse(
            message="If that email exists, a password reset link has been sent."
        )
    except Exception as e:
        # Don't reveal errors
        return MessageResponse(
            message="If that email exists, a password reset link has been sent."
        )

@app.post("/auth/reset-password", response_model=MessageResponse)
def reset_password_endpoint(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with token from email"""
    try:
        reset_password(db, req.token, req.new_password)
        return MessageResponse(message="Password reset successful! You can now log in.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/auth/resend-verification", response_model=MessageResponse)
def resend_verification(email: EmailStr, db: Session = Depends(get_db)):
    """Resend verification email"""
    from .database import get_user_by_email
    
    user = get_user_by_email(db, email)
    if not user:
        return MessageResponse(message="If that email exists, verification email sent.")
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    token = create_verification_token(email)
    send_verification_email(email, token)
    
    return MessageResponse(message="Verification email sent.")

# ============ CHAT ENDPOINTS ============

@app.get("/chat/history/{user_id}", response_model=ChatHistoryResponse)
def get_chat_history(user_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """Get chat history for a user"""
    # Verify user exists
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    try:
        from .database import get_user_chat_history
        messages = get_user_chat_history(db, user_id, limit)
        
        # Format messages for frontend
        formatted_messages = [
            {
                "id": msg.id,
                "message": msg.message,
                "response": msg.response,
                "sentiment": msg.sentiment,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            }
            for msg in messages
        ]
        
        return ChatHistoryResponse(messages=formatted_messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Send a chat message with chat memory"""
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    # Verify user exists
    user = get_user_by_id(db, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    try:
        # Build context from chat history
        context = ""
        if req.chat_history:
            context = "\nRecent conversation:\n"
            for hist_msg in req.chat_history[-10:]:  # Last 10 messages
                role_label = "User" if hist_msg.role == "user" else "Assistant"
                context += f"{role_label}: {hist_msg.content}\n"
            context += f"\nCurrent message: {msg}\n"
        
        # Get response with context
        prompt_with_context = context + msg if context else msg
        reply = route_by_sentiment(prompt_with_context)
        
        # Save to database
        save_chat_message(
            db=db,
            user_id=req.user_id,
            message=msg,
            response=reply,
            sentiment="auto"
        )
        
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ HEALTH CHECK ============

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Server is running"}

# Mount static files (frontend)
app.mount(
    "/",
    StaticFiles(directory="chat_ui", html=True),
    name="static"
)