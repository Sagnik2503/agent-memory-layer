from app.db.database import Sessionlocal
from app.db.models import ExpenseDB
from app.graph.state import Expense


def save_expense(expense: Expense) -> ExpenseDB:

    db = Sessionlocal()
    try:
        expense_row = ExpenseDB(
            amount=expense.amount,
            currency=expense.currency,
            merchant=expense.merchant,
            category=expense.category,
            subcategory=expense.subcategory,
            date=expense.date,
            description=expense.description,
        )
        db.add(expense_row)
        db.commit()
        db.refresh(expense_row)

        return expense_row
    finally:
        db.close()
