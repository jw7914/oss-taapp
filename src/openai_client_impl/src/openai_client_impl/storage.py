"""Secure storage for OpenAI API keys and conversation data using SQLAlchemy and Fernet encryption.

This module provides database persistence functionality as an internal implementation detail
of the openai_client_impl component. The database logic is encapsulated within this component
and does not leak into the abstract port (openai_service_api).

"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./.data/app.db")
FERNET_KEY = os.getenv("FERNET_KEY")

_engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for SQLAlchemy models."""


class UserCred(Base):
    """User credentials storage model."""

    __tablename__ = "user_cred"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    openai_api_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConversationStore(Base):
    """Conversation storage model."""

    __tablename__ = "conversation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conv_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subject: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[str] = mapped_column(String(255))
    messages_json: Mapped[str] = mapped_column(Text)


def init_db() -> None:
    """Initialize the database by creating all tables."""
    Path(".data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(_engine)


def _fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption.

    If FERNET_KEY is not set, generates a new key and saves it to .fernet_key file.
    """
    if not FERNET_KEY:
        key_file = Path(".fernet_key")
        if key_file.exists():
            fernet_key: bytes = key_file.read_bytes()
        else:
            fernet_key = Fernet.generate_key()
            Path(".data").mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(fernet_key)
    else:
        fernet_key = FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY
    return Fernet(fernet_key)


def set_openai_key(subject: str, api_key_plain: str) -> None:
    """Set the OpenAI API key for a subject, encrypting it before storage."""
    f = _fernet()
    enc = f.encrypt(api_key_plain.encode()).decode()
    with SessionLocal() as db:
        row = db.query(UserCred).filter_by(subject=subject).one_or_none()
        if not row:
            row = UserCred(subject=subject)
            db.add(row)
        row.openai_api_key_enc = enc
        db.commit()


def get_openai_key(subject: str) -> str | None:
    """Get the OpenAI API key for a subject, decrypting it from storage."""
    with SessionLocal() as db:
        row = db.query(UserCred).filter_by(subject=subject).one_or_none()
        if not row or not row.openai_api_key_enc:
            return None
        f = _fernet()
        decrypted_bytes: bytes = f.decrypt(row.openai_api_key_enc.encode())
        return decrypted_bytes.decode()


def save_conversation(
    conv_id: str,
    subject: str,
    created_at: str,
    messages_json: str,
) -> None:
    """Save a conversation to the database."""
    with SessionLocal() as db:
        row = db.query(ConversationStore).filter_by(conv_id=conv_id).one_or_none()
        if not row:
            row = ConversationStore(
                conv_id=conv_id,
                subject=subject,
                created_at=created_at,
                messages_json=messages_json,
            )
            db.add(row)
        else:
            row.messages_json = messages_json
        db.commit()


def get_conversation_data(conv_id: str) -> tuple[str, str, str] | None:
    """Get conversation data from the database.

    Returns:
        Tuple of (subject, created_at, messages_json) or None if not found.

    """
    with SessionLocal() as db:
        row = db.query(ConversationStore).filter_by(conv_id=conv_id).one_or_none()
        if not row:
            return None
        return (row.subject, row.created_at, row.messages_json)


def delete_conversation(conv_id: str) -> bool:
    """Delete a conversation from the database.

    Returns:
        True if deleted, False if not found.

    """
    with SessionLocal() as db:
        row = db.query(ConversationStore).filter_by(conv_id=conv_id).one_or_none()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True
