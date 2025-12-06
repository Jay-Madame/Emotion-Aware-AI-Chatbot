# src/auth.py
import os
import smtplib
import threading
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    verify_user,
    create_reset_token,
    get_reset_token,
    mark_token_used,
    update_user_password
)

# ============ SECURITY CONFIGURATION ============

# Password hashing
# Disable truncate_error since we use SHA256 pre-hashing for unlimited length support
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__truncate_error=False  # We handle long passwords with SHA256 pre-hashing
)

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_SERVER)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ============ PASSWORD HASHING ============

def hash_password(password: str) -> str:
    """
    Hash a password with unlimited length support.
    Uses SHA256 pre-hashing to bypass Bcrypt's 72-byte limit.
    """
    import hashlib
    
    # Pre-hash with SHA256 to support unlimited password length
    # This is a standard approach used by many security libraries
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # Now hash with bcrypt (which is always 64 hex chars, well under 72 bytes)
    return pwd_context.hash(sha256_hash)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash (supports unlimited length).
    Uses SHA256 pre-hashing to bypass Bcrypt's 72-byte limit.
    """
    import hashlib
    
    # Pre-hash with SHA256 (same as in hash_password)
    sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    
    # Verify against the bcrypt hash
    return pwd_context.verify(sha256_hash, hashed_password)

# ============ JWT TOKEN FUNCTIONS ============

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_verification_token(email: str) -> str:
    """Create an email verification token"""
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"email": email, "exp": expire, "type": "verification"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_password_reset_token(email: str) -> str:
    """Create a password reset token"""
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {"email": email, "exp": expire, "type": "password_reset"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

# ============ EMAIL FUNCTIONS ============

def send_email(to_email: str, subject: str, body: str):
    """Send an email (configure SMTP settings in .env)"""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"⚠️  Email not configured. Would send to {to_email}:")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_verification_email(email: str, token: str):
    """Send email verification link"""
    verification_link = f"{FRONTEND_URL}/verify-email.html?token={token}"
    
    subject = "Verify Your Email - Knight Bot"
    body = f"""
    <html>
    <body>
        <h2>Welcome to Knight Bot!</h2>
        <p>Please verify your email address by clicking the link below:</p>
        <p><a href="{verification_link}">Verify Email</a></p>
        <p>Or copy and paste this link into your browser:</p>
        <p>{verification_link}</p>
        <p>This link will expire in 24 hours.</p>
        <br>
        <p>If you didn't create this account, please ignore this email.</p>
    </body>
    </html>
    """
    
    send_email(email, subject, body)

def send_password_reset_email(email: str, token: str):
    """Send password reset link"""
    reset_link = f"{FRONTEND_URL}/reset-password.html?token={token}"
    
    subject = "Reset Your Password - Knight Bot"
    body = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_link}">Reset Password</a></p>
        <p>Or copy and paste this link into your browser:</p>
        <p>{reset_link}</p>
        <p>This link will expire in 1 hour.</p>
        <br>
        <p>If you didn't request a password reset, please ignore this email.</p>
    </body>
    </html>
    """
    
    send_email(email, subject, body)

# ============ AUTHENTICATION FUNCTIONS ============

def register_user(db: Session, username: str, email: str, password: str):
    """Register a new user"""
    # Check if username exists
    if get_user_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = hash_password(password)
    user = create_user(db, username, email, hashed_password)
    
    # Send verification email in background thread (async)
    token = create_verification_token(email)
    email_thread = threading.Thread(
        target=send_verification_email,
        args=(email, token),
        daemon=True
    )
    email_thread.start()
    
    print(f"✅ User {username} registered. Verification email sending in background...")
    
    return user

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user by username and password"""
    user = get_user_by_username(db, username)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email for verification link."
        )
    
    return user

def verify_user_email(db: Session, token: str):
    """Verify user's email with token"""
    try:
        payload = decode_token(token)
        email = payload.get("email")
        token_type = payload.get("type")
        
        if token_type != "verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        verify_user(db, email)
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification token"
        )

def request_password_reset(db: Session, email: str):
    """Request a password reset"""
    user = get_user_by_email(db, email)
    
    # Don't reveal if email exists or not (security best practice)
    if not user:
        return
    
    # Create reset token
    token = create_password_reset_token(email)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    create_reset_token(db, email, token, expires_at)
    
    # Send reset email in background thread (async)
    email_thread = threading.Thread(
        target=send_password_reset_email,
        args=(email, token),
        daemon=True
    )
    email_thread.start()
    
    print(f"✅ Password reset requested for {email}. Email sending in background...")

def reset_password(db: Session, token: str, new_password: str):
    """Reset password with token"""
    try:
        payload = decode_token(token)
        email = payload.get("email")
        token_type = payload.get("type")
        
        if token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Check if token exists in database and hasn't been used
        db_token = get_reset_token(db, token)
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used token"
            )
        
        # Check if token has expired
        if datetime.utcnow() > db_token.expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token has expired"
            )
        
        # Update password
        hashed_password = hash_password(new_password)
        update_user_password(db, email, hashed_password)
        
        # Mark token as used
        mark_token_used(db, db_token.id)
        
        return True
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token"
        )