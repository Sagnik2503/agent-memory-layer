import pytest
from app.graph.state import Expense, ValidationResult

def test_expense_model_valid():
    expense = Expense(
        amount=500.0,
        currency="INR",
        merchant="Swiggy",
        category="food",
        subcategory="delivery",
        date="2026-08-25",
        description="lunch"
    )
    assert expense.amount == 500.0
    assert expense.currency == "INR"
    assert expense.merchant == "Swiggy"
    assert expense.category == "food"

def test_expense_model_minimal():
    expense = Expense(
        amount=100.0,
        currency="INR",
        category="food"
    )
    assert expense.amount == 100.0
    assert expense.merchant is None

def test_validation_result_valid():
    result = ValidationResult(
        is_valid=True,
        errors=[],
        missing_fields=[]
    )
    assert result.is_valid is True

def test_validation_result_invalid():
    result = ValidationResult(
        is_valid=False,
        errors=["Amount must be greater than 0"],
        missing_fields=["amount"]
    )
    assert result.is_valid is False
    assert len(result.errors) == 1
