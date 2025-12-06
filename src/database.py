# src/database.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Determine database URL
TESTING = os.getenv("TESTING") == "1"

if TESTING:
    DATABASE_URL = "sqlite:///:memory:"  # in-memory DB for tests
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============ DATABASE MODELS ============
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    sentiment = Column(String(20))
    timestamp = Column(DateTime, default=datetime.utcnow)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============ DATABASE FUNCTIONS ============
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized")

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============ USER OPERATIONS ============

def get_user_by_username(db: Session, username: str):
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, username: str, email: str, hashed_password: str):
    """Create a new user"""
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_verified=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_user(db: Session, email: str):
    """Mark user as verified"""
    user = get_user_by_email(db, email)
    if user:
        user.is_verified = True
        db.commit()
        db.refresh(user)
    return user

# ============ CHAT MESSAGE OPERATIONS ============

def save_chat_message(db: Session, user_id: int, message: str, response: str, sentiment: str = None):
    """Save a chat message to the database"""
    chat_msg = ChatMessage(
        user_id=user_id,
        message=message,
        response=response,
        sentiment=sentiment
    )
    db.add(chat_msg)
    db.commit()
    db.refresh(chat_msg)
    return chat_msg

def get_user_chat_history(db: Session, user_id: int, limit: int = 50):
    """Get chat history for a user"""
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
        .all()
    )

# ============ PASSWORD RESET TOKEN OPERATIONS ============

def create_reset_token(db: Session, email: str, token: str, expires_at: datetime):
    """Create a password reset token"""
    reset_token = PasswordResetToken(
        email=email,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token

def get_reset_token(db: Session, token: str):
    """Get a password reset token"""
    return (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == token,
            PasswordResetToken.used == False
        )
        .first()
    )

def mark_token_used(db: Session, token_id: int):
    """Mark a reset token as used"""
    token = db.query(PasswordResetToken).filter(PasswordResetToken.id == token_id).first()
    if token:
        token.used = True
        db.commit()

def update_user_password(db: Session, email: str, new_hashed_password: str):
    """Update user's password"""
    user = get_user_by_email(db, email)
    if user:
        user.hashed_password = new_hashed_password
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user