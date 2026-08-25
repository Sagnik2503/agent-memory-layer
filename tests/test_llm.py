import pytest
from app.llm.model import LLMClient
from app.models.expense import Expense

def test_llm_client_initialization():
    client = LLMClient()
    assert client.client is not None

def test_classify_intent_expense():
    client = LLMClient()
    assert hasattr(client, 'classify_intent')
    assert hasattr(client, 'extract_expense')

def test_extract_expense_returns_expense_object():
    client = LLMClient()
    import inspect
    sig = inspect.signature(client.extract_expense)
    assert sig.return_annotation == Expense