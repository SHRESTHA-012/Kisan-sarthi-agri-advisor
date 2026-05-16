
import time
import json
from typing import Optional
from dataclasses import dataclass, field, asdict


# Session expires after 30 minutes of inactivity
SESSION_TTL_SECONDS = 30 * 60

# Conversation states
class State:
    IDLE           = "idle"           # No active flow
    AWAITING_CROP  = "awaiting_crop"  # Asked user to name their crop
    AWAITING_IMAGE = "awaiting_image" # Asked user to send pest/disease image
    IN_ADVISORY    = "in_advisory"    # Mid-advisory conversation
    AWAITING_AREA  = "awaiting_area"  # Asked for field area (for fertilizer calc)


@dataclass
class FarmerSession:
    user_id: int
    username: Optional[str] = None
    language: str = "hi"                    # Default Hindi; "en" or "bho" (Bhojpuri)
    state: str = State.IDLE
    current_crop: Optional[str] = None
    district: Optional[str] = None         # Bihar district for localized advice
    last_active: float = field(default_factory=time.time)
    context: dict = field(default_factory=dict)  # Arbitrary per-flow context

    def touch(self):
        """Update last-active timestamp."""
        self.last_active = time.time()

    def reset(self):
        """Reset to idle state, keeping user prefs."""
        self.state = State.IDLE
        self.context = {}

    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TTL_SECONDS

    def to_dict(self) -> dict:
        return asdict(self)


class SessionManager:
    """
    In-memory session store. 
    For production, swap _store with Redis using the same interface.
    """

    def __init__(self):
        self._store: dict[int, FarmerSession] = {}

    def get(self, user_id: int) -> FarmerSession:
        """Return existing session or create a new one."""
        session = self._store.get(user_id)
        if session is None or session.is_expired():
            session = FarmerSession(user_id=user_id)
            self._store[user_id] = session
        session.touch()
        return session

    def update(self, session: FarmerSession) -> None:
        """Persist session changes back to store."""
        session.touch()
        self._store[session.user_id] = session

    def clear(self, user_id: int) -> None:
        """Force-clear a session (e.g. on /start or /reset)."""
        self._store.pop(user_id, None)

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Call periodically."""
        expired = [uid for uid, s in self._store.items() if s.is_expired()]
        for uid in expired:
            del self._store[uid]
        return len(expired)

    def stats(self) -> dict:
        """Active session count for monitoring."""
        return {
            "active_sessions": len(self._store),
            "users": [s.user_id for s in self._store.values()],
        }


# Singleton instance shared across the app
session_manager = SessionManager()
