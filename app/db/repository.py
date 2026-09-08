from app.db.database import Sessionlocal
from app.db.models import ExpenseDB
from app.graph.state import Expense, ExpenseQuery


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


def get_expense(expense_query: ExpenseQuery) -> list[ExpenseDB]:
    db = Sessionlocal()

    try:
        query = db.query(ExpenseDB)

        if expense_query.start_date:
            query = query.where(ExpenseDB.date >= expense_query.start_date)

        if expense_query.end_date:
            query = query.where(ExpenseDB.date <= expense_query.end_date)

        if expense_query.merchant:
            query = query.where(ExpenseDB.merchant.in_(expense_query.merchant))

        if expense_query.category:
            query = query.where(ExpenseDB.category.in_(expense_query.category))

        query = query.order_by(ExpenseDB.date.desc())

        return query.all()

    finally:
        db.close()
