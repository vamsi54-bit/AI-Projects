"""Days 5–6 wire contract. Health uses the connection turn; chat uses a unique request turn."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Envelope(StrictModel):
    event_id: UUID
    session_id: UUID
    request_id: UUID
    turn_id: UUID
    sequence: int = Field(strict=True, ge=1, le=9_007_199_254_740_991)
    timestamp: AwareDatetime
    agent: Literal["system", "supervisor"]

    @field_validator("event_id", "session_id", "request_id", "turn_id", mode="before")
    @classmethod
    def canonical_uuid(cls, value):
        if isinstance(value, UUID):
            return value
        if not isinstance(value, str) or len(value) != 36 or str(UUID(value)) != value.lower():
            raise ValueError("Expected a canonical UUID")
        return value

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_string(cls, value):
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or "T" not in value or not (value.endswith("Z") or value.endswith("+00:00")):
            raise ValueError("Expected a UTC ISO timestamp")
        return value

class EmptyPayload(StrictModel):
    pass

class HealthPing(Envelope):
    agent: Literal["system"]
    type: Literal["health.ping"]
    payload: EmptyPayload

class ReadyPayload(StrictModel):
    protocol_version: Literal[2] = 2
    capabilities: tuple[str, ...] = ("health", "chat", "transcription")
    provider_ready: bool = False

class SessionReady(Envelope):
    type: Literal["session.ready"] = "session.ready"
    payload: ReadyPayload = Field(default_factory=ReadyPayload)

class PongPayload(StrictModel):
    status: Literal["ok"] = "ok"
    service: Literal["voiceteam-api"] = "voiceteam-api"

class HealthPong(Envelope):
    type: Literal["health.pong"] = "health.pong"
    payload: PongPayload = Field(default_factory=PongPayload)

ErrorCode = Literal["INVALID_MESSAGE", "WRONG_SESSION", "INVALID_TURN", "STALE_EVENT", "DUPLICATE_EVENT", "SESSION_EXPIRED", "TOO_MANY_MESSAGES"]
class ErrorPayload(StrictModel):
    code: ErrorCode
    message: str = Field(min_length=1, max_length=160)

class ErrorEvent(Envelope):
    type: Literal["error"] = "error"
    payload: ErrorPayload

class ChatPayload(StrictModel):
    text: str = Field(strict=True, min_length=1, max_length=1200)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("A question cannot be blank")
        return value.strip()

class ChatSend(Envelope):
    type: Literal["chat.send"]
    agent: Literal["system"]
    payload: ChatPayload
