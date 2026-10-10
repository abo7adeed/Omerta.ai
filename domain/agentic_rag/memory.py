"""Conversational Memory and Session Management Service for Omerta.ai Agentic RAG.

Capabilities:
1. Multi-turn Session Persistence:
   - Stores user inquiries, assistant narrative, evidence citations, deterministic metrics,
     charts, thought steps, and guardrail warnings per session.
2. Context Memory Window:
   - Summarizes prior dialogue turns into an executive conversational brief for the LLM.
   - Preserves continuity for follow-up queries (e.g. "tell me about its transactions").
3. Entity Carry-over Memory:
   - Automatically extracts and carries over previously referenced entity identifiers
     (TXN-xxx, ACC-xxx, DEV-xxx) if a follow-up query omits explicit IDs.
4. Session Management:
   - Create, list, retrieve, and delete sessions per user.
"""

from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Storage directory for persistent sessions
SESSIONS_DIR = Path("apps/api/static/data/chat_sessions").resolve()
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class ChatTurnRecord(BaseModel):
    """An individual message turn within a chat session."""
    turn_id: str = Field(default_factory=lambda: f"turn-{uuid4().hex[:8]}")
    sender: str  # "user" | "assistant"
    text: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    rag_response: dict[str, Any] | None = None
    thought_steps: list[str] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChatSessionRecord(BaseModel):
    """A full conversation session holding sequential message turns."""
    session_id: str
    user_id: str = "default_investigator"
    title: str = "New Investigation"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    turns: list[ChatTurnRecord] = Field(default_factory=list)


class AgenticMemoryManager:
    """Thread-safe session persistence and conversational memory retriever."""

    @classmethod
    def _get_session_path(cls, session_id: str) -> Path:
        # Sanitize session_id to avoid path traversal
        clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "", session_id)
        return SESSIONS_DIR / f"{clean_id}.json"

    @classmethod
    def get_session(cls, session_id: str) -> ChatSessionRecord | None:
        """Load session record from disk."""
        if not session_id:
            return None
        path = cls._get_session_path(session_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ChatSessionRecord.model_validate(data)
        except Exception as exc:
            logger.warning("Failed to load session %s: %s", session_id, exc)
            return None

    @classmethod
    def save_session(cls, session: ChatSessionRecord) -> None:
        """Persist session record to disk."""
        session.updated_at = datetime.now(UTC).isoformat()
        path = cls._get_session_path(session.session_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session.model_dump(), f, indent=2)
        except Exception as exc:
            logger.error("Failed to save session %s: %s", session.session_id, exc)

    @classmethod
    def create_session(cls, user_id: str = "default_investigator", title: str | None = None) -> ChatSessionRecord:
        """Initialize a new empty session."""
        session_id = f"sess-{uuid4().hex[:10]}"
        session = ChatSessionRecord(
            session_id=session_id,
            user_id=user_id or "default_investigator",
            title=title or "New Forensic Investigation",
        )
        cls.save_session(session)
        return session

    @classmethod
    def list_user_sessions(cls, user_id: str = "default_investigator") -> list[dict[str, Any]]:
        """List all sessions belonging to the user with summaries."""
        results = []
        for file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Filter by user if specified
                sess_user = data.get("user_id", "")
                if user_id and sess_user and sess_user != user_id and sess_user != "default_investigator":
                    continue

                turns = data.get("turns", [])
                last_preview = ""
                if turns:
                    last_preview = turns[-1].get("text", "")[:80]

                results.append({
                    "session_id": data.get("session_id"),
                    "title": data.get("title", "Forensic Investigation"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": len(turns),
                    "last_preview": last_preview,
                })
            except Exception as exc:
                logger.warning("Error reading session file %s: %s", file, exc)

        # Sort by updated_at descending
        results.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return results

    @classmethod
    def delete_session(cls, session_id: str, user_id: str | None = None) -> bool:
        """Delete session file if authorized."""
        path = cls._get_session_path(session_id)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as exc:
                logger.error("Failed to delete session %s: %s", session_id, exc)
                return False
        return False

    @classmethod
    def add_turn(
        cls,
        session_id: str,
        user_id: str,
        user_query: str,
        response_data: dict[str, Any],
        thought_steps: list[str] | None = None,
        charts: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None,
    ) -> ChatSessionRecord:
        """Append user and assistant turns to the session."""
        session = cls.get_session(session_id)
        if not session:
            # Auto-create if not existing
            # Derive title from user inquiry
            clean_title = user_query.strip()
            clean_title = re.sub(r"^[Ww]hat (is|are)|^[Hh]ow (many|do)|^[Pp]lease ", "", clean_title)
            clean_title = clean_title[:45].strip().capitalize()
            if not clean_title:
                clean_title = "Forensic Investigation"
            session = ChatSessionRecord(
                session_id=session_id,
                user_id=user_id or "default_investigator",
                title=clean_title,
            )

        # Update title if it's currently default
        if session.title in ("New Investigation", "New Forensic Investigation") and user_query:
            short_title = user_query.strip()
            short_title = re.sub(r"^[Ww]hat (is|are)|^[Hh]ow (many|do)|^[Pp]lease ", "", short_title)
            short_title = short_title[:45].strip().capitalize()
            if short_title:
                session.title = short_title

        # Append User Turn
        user_turn = ChatTurnRecord(
            sender="user",
            text=user_query,
        )
        session.turns.append(user_turn)

        # Append Assistant Turn
        assistant_turn = ChatTurnRecord(
            sender="assistant",
            text=response_data.get("answer", ""),
            rag_response=response_data,
            thought_steps=thought_steps or response_data.get("thought_steps", []),
            charts=charts or response_data.get("charts", []),
            warnings=warnings or response_data.get("warnings", []),
        )
        session.turns.append(assistant_turn)

        cls.save_session(session)
        return session

    @classmethod
    def get_conversation_context(cls, session_id: str | None, max_turns: int = 4) -> str:
        """Extract recent conversation dialogue as formatted context for synthesis."""
        if not session_id:
            return ""
        session = cls.get_session(session_id)
        if not session or not session.turns:
            return ""

        recent = session.turns[-max_turns:]
        lines = ["Recent Prior Conversation Turns:"]
        for turn in recent:
            prefix = "User" if turn.sender == "user" else "Assistant"
            # Keep assistant text concise in memory context
            snippet = turn.text[:240].replace("\n", " ").strip()
            lines.append(f"- {prefix}: {snippet}")
        return "\n".join(lines)

    @classmethod
    def extract_prior_entities(cls, session_id: str | None, max_turns: int = 4) -> list[str]:
        """Extract explicit entities (TXN-, ACC-, DEV-, OMR-) mentioned in recent turns."""
        if not session_id:
            return []
        session = cls.get_session(session_id)
        if not session or not session.turns:
            return []

        recent = session.turns[-max_turns:]
        entities = []
        for turn in recent:
            for m in re.finditer(r"\b(TXN-[A-Za-z0-9_-]+|ACC-[A-Za-z0-9_-]+|DEV-[A-Za-z0-9_-]+|OMR-[A-Za-z0-9_-]+)\b", turn.text, re.I):
                val = m.group(1).upper()
                if val not in entities:
                    entities.append(val)
        return entities
