"""Database models and session management."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine
from app.config import DATABASE_URL, DATA_DIR

# SQLite needs a path, not a URL — and check_same_thread=False for FastAPI
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relations
    search_config = relationship("SearchConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


class SearchConfig(Base):
    __tablename__ = "search_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Search parameters
    job_titles = Column(Text, nullable=False, default="CTO, Chief Technology Officer")  # comma-separated
    locations = Column(Text, nullable=False, default="London")  # comma-separated
    salary_min = Column(Integer, nullable=False, default=150000)
    salary_max = Column(Integer, nullable=True)
    exclusions = Column(Text, default="")  # comma-separated company names

    # Delivery preferences
    telegram_enabled = Column(Boolean, default=False)
    telegram_chat_id = Column(String, nullable=True)
    telegram_bot_token = Column(String, nullable=True)  # per-user override

    # Schedule
    run_hour = Column(Integer, default=7)  # 7am local
    is_active = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="search_config")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    score = Column(Float, default=0.0)
    fit_notes = Column(Text, nullable=True)
    is_seen = Column(Boolean, default=False)
    is_favourite = Column(Boolean, default=False)
    is_excluded = Column(Boolean, default=False)

    # Metadata
    source = Column(String, nullable=True)  # e.g. "LinkedIn", "Otta"
    scraped_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="jobs")


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    jobs_found = Column(Integer, default=0)
    jobs_filtered = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    status = Column(String, default="running")  # running, completed, failed
    error = Column(Text, nullable=True)
