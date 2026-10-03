from datetime import datetime
from pydantic import BaseModel, Field

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    history: list[dict] = Field(default_factory=list, max_length=20)

class Citation(BaseModel):
    document_id: int
    title: str
    chunk_index: int
    snippet: str
    score: float

class ChatOut(BaseModel):
    answer: str
    why_this_is_happening: str | None = None
    diagnostic_state: dict | None = None
    ai_provider: str | None = None
    llm_used: bool = False
    diagnosis: str | None = None
    severity: str | None = None
    category: str | None = None
    steps: list[str] = []
    tools_used: list[str] = []
    citations: list[Citation] = []

class TicketCreate(BaseModel):
    title: str
    description: str
    category: str = "General"
    priority: str = "medium"

class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    ai_summary: str | None
    resolution: str | None
    created_at: datetime
    updated_at: datetime

class MemoryOut(BaseModel):
    key: str
    value: str
