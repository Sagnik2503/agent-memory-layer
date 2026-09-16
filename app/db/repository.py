from app.db.database import Sessionlocal
from app.db.models import ExpenseDB
from app.agent.state import ExpenseInput


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


# def get_expense(expense_query: ExpenseQuery) -> list[Expense]:
#     db = Sessionlocal()

#     try:
#         query = db.query(ExpenseDB)

#         if expense_query.start_date:
#             query = query.where(ExpenseDB.date >= expense_query.start_date)

#         if expense_query.end_date:
#             query = query.where(ExpenseDB.date <= expense_query.end_date)

#         if expense_query.merchant:
#             query = query.where(ExpenseDB.merchant.in_(expense_query.merchant))

#         if expense_query.category:
#             query = query.where(ExpenseDB.category.in_(expense_query.category))

#         query = query.order_by(ExpenseDB.date.desc())
#         results = query.all()

#         return [
#             Expense(
#                 amount=r.amount,
#                 currency=r.currency,
#                 merchant=r.merchant,
#                 category=r.category,
#                 subcategory=r.subcategory,
#                 date=r.date,
#                 description=r.description,
#             )
#             for r in results
#         ]

#     finally:
#         db.close()
