from pydantic import BaseModel
from typing import Optional


class ClarificationMessage(BaseModel):
    user: str
    assistant: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    clarification_history: Optional[list[ClarificationMessage]] = None
    clarification_rounds: int = 0


class ChatResponse(BaseModel):
    response: str
    needs_clarification: bool = False
    clarification_history: list[ClarificationMessage] = []
    clarification_rounds: int = 0
