"""Shared test fixtures.

Sets up an isolated SQLite database for the whole pytest session BEFORE any
app module is imported, so tests never touch the developer's live expense.db.
"""

import os
import tempfile
from datetime import date, timedelta

import pytest

_TEST_DB_DIR = tempfile.mkdtemp(prefix="expense-tracker-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/expense.db"

from app.config import DEFAULT_USER_ID  # noqa: E402  (after DATABASE_URL is set)


def _first_of_previous_month(today: date) -> date:
    first_of_month = today.replace(day=1)
    return (first_of_month - timedelta(days=1)).replace(day=1)


def build_seed_expenses(today: date | None = None) -> list[dict]:
    """Known-good seed rows: two months, two currencies, one expense per
    canonical ExpenseCategory (see GLOSSARY.md)."""
    today = today or date.today()
    prev = _first_of_previous_month(today)
    return [
        {
            "user_id": DEFAULT_USER_ID,
            "date": today.replace(day=2),
            "merchant": "Cafe Mocha",
            "category": "food",
            "subcategory": "coffee",
            "amount": 250.0,
            "currency": "INR",
        },
        {
            "user_id": DEFAULT_USER_ID,
            "date": today.replace(day=3),
            "merchant": "Uber",
            "category": "transport",
            "subcategory": "commute",
            "amount": 18.75,
            "currency": "USD",
        },
        {
            "user_id": DEFAULT_USER_ID,
            "date": today.replace(day=5),
            "merchant": "Uniqlo",
            "category": "shopping",
            "subcategory": "clothes",
            "amount": 120.0,
            "currency": "USD",
        },
        {
            "user_id": DEFAULT_USER_ID,
            "date": today.replace(day=1),
            "merchant": "Electricity Board",
            "category": "bills",
            "subcategory": "utilities",
            "amount": 2100.0,
            "currency": "INR",
        },
        {
            "user_id": DEFAULT_USER_ID,
            "date": prev.replace(day=15),
            "merchant": "Netflix",
            "category": "entertainment",
            "subcategory": "streaming",
            "amount": 15.99,
            "currency": "USD",
        },
        {
            "user_id": DEFAULT_USER_ID,
            "date": prev.replace(day=20),
            "merchant": "Pharmacy",
            "category": "health",
            "subcategory": "medicine",
            "amount": 450.0,
            "currency": "INR",
        },
        {
            "user_id": DEFAULT_USER_ID,
            "date": prev.replace(day=12),
            "merchant": "Salon",
            "category": "personal_care",
            "subcategory": "haircut",
            "amount": 600.0,
            "currency": "INR",
        },
        {
            "user_id": DEFAULT_USER_ID,
            "date": prev.replace(day=25),
            "merchant": "Corner Shop",
            "category": "other",
            "subcategory": "gift",
            "amount": 30.0,
            "currency": "USD",
        },
    ]


@pytest.fixture()
def seeded_db():
    """Recreate the expenses table and insert the seed rows for one test.

    Budgets are cleared too, so every test starts from zero budgets and can
    seed its own via the seed_budgets fixture.
    """
    from app.db.database import Base, Sessionlocal, engine
    from app.db.models import BudgetDB, ExpenseDB

    Base.metadata.create_all(bind=engine)

    rows = build_seed_expenses()
    with Sessionlocal() as db:
        db.query(ExpenseDB).delete()
        db.query(BudgetDB).delete()
        for row in rows:
            db.add(ExpenseDB(**row))
        db.commit()

    return rows


@pytest.fixture()
def seed_budgets():
    """Replace the user's monthly budgets with (category, amount) rows.

    ``category`` of None is the overall Budget (see GLOSSARY.md).
    """
    from app.db.database import Sessionlocal
    from app.db.models import BudgetDB

    def _seed(rows):
        with Sessionlocal() as db:
            db.query(BudgetDB).delete()
            for category, amount in rows:
                db.add(
                    BudgetDB(
                        user_id=DEFAULT_USER_ID,
                        category=category,
                        amount=amount,
                        period="monthly",
                    )
                )
            db.commit()

    return _seed


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)
