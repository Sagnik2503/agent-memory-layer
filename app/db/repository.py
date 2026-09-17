from app.db.database import Sessionlocal
from app.db.models import ExpenseDB
from app.agent.state import ExpenseInput, ExpenseQuery, ExpenseResult, ExpenseUpdate
from sqlalchemy import func


def save_expense(expense: ExpenseInput) -> ExpenseDB:

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


def get_expense(expense_query: ExpenseQuery) -> list[ExpenseResult]:
    db = Sessionlocal()

    try:
        query = db.query(ExpenseDB)

        if expense_query.start_date:
            query = query.where(ExpenseDB.date >= expense_query.start_date)

        if expense_query.end_date:
            query = query.where(ExpenseDB.date <= expense_query.end_date)

        if expense_query.merchant:
            merchants = [m.lower() for m in expense_query.merchant]

            query = query.where(func.lower(ExpenseDB.merchant).in_(merchants))

        if expense_query.category:
            categories = [c.lower() for c in expense_query.category]

            query = query.where(func.lower(ExpenseDB.category).in_(categories))

        if expense_query.subcategories:
            subcategories = [s.lower() for s in expense_query.subcategories]

            query = query.where(func.lower(ExpenseDB.subcategory).in_(subcategories))

        query = query.order_by(ExpenseDB.date.desc())

        results = query.all()

        return [
            ExpenseResult(
                id=r.id,
                amount=r.amount,
                currency=r.currency,
                merchant=r.merchant,
                category=r.category,
                subcategory=r.subcategory,
                date=r.date,
                description=r.description,
            )
            for r in results
        ]

    finally:
        db.close()


def update_expenses(updates: list[ExpenseUpdate]) -> list[ExpenseDB]:

    db = Sessionlocal()

    try:
        updated_expenses = []

        for update in updates:
            expense = (
                db.query(ExpenseDB).filter(ExpenseDB.id == update.expense_id).first()
            )

            if not expense:
                continue

            update_data = update.model_dump(exclude={"expense_id"}, exclude_none=True)

            for field, value in update_data.items():
                setattr(expense, field, value)

            updated_expenses.append(expense)

        db.commit()

        for expense in updated_expenses:
            db.refresh(expense)

        return updated_expenses

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def delete_expenses(expense_ids: list[int]) -> list[int]:
    db = Sessionlocal()

    try:
        deleted = []
        for eid in expense_ids:
            expense = db.query(ExpenseDB).filter(ExpenseDB.id == eid).first()
            if expense:
                db.delete(expense)
                deleted.append(eid)
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
