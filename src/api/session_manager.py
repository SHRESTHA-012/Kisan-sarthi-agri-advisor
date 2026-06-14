import time
from typing import Optional
from dataclasses import dataclass, field, asdict


SESSION_TTL_SECONDS = 30 * 60


class State:
    IDLE           = "idle"
    AWAITING_CROP  = "awaiting_crop"
    AWAITING_IMAGE = "awaiting_image"
    IN_ADVISORY    = "in_advisory"
    AWAITING_AREA  = "awaiting_area"


@dataclass
class FarmerSession:
    user_id: int
    username: Optional[str] = None
    language: str = "hi"
    state: str = State.IDLE
    current_crop: Optional[str] = None
    district: Optional[str] = None
    last_active: float = field(default_factory=time.time)
    context: dict = field(default_factory=dict)

    def touch(self):
        self.last_active = time.time()

    def reset(self):
        self.state   = State.IDLE
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
        session = self._store.get(user_id)
        if session is None or session.is_expired():
            session = FarmerSession(user_id=user_id)
            self._store[user_id] = session
        session.touch()
        return session

    def update(self, session: FarmerSession) -> None:
        session.touch()
        self._store[session.user_id] = session

    def clear(self, user_id: int) -> None:
        self._store.pop(user_id, None)

    def cleanup_expired(self) -> int:
        expired = [uid for uid, s in self._store.items() if s.is_expired()]
        for uid in expired:
            del self._store[uid]
        return len(expired)

    def stats(self) -> dict:
        return {
            "active_sessions": len(self._store),
            "users": [s.user_id for s in self._store.values()],
        }


session_manager = SessionManager()
