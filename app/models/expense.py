from pydantic import BaseModel
from typing import Optional

class Expense(BaseModel):
    amount: float
    currency: str
    merchant: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None

class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]
    missing_fields: list[str]

class ClarityCheck(BaseModel):
    is_clear: bool
    missing_fields: list[str]
    clarification_question: str
