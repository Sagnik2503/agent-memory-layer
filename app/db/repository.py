from app.db.database import Sessionlocal
from app.db.models import ExpenseDB, SubscriptionDB, BudgetDB
from app.agent.state import (
    ExpenseInput,
    ExpenseQuery,
    ExpenseResult,
    ExpenseUpdate,
    SubscriptionResponse,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionDelete,
    ExpenseCategory,
)
from datetime import datetime, date, timedelta
import calendar
from sqlalchemy import func


def save_expense(
    user_id: str, expense: ExpenseInput, subscription_id: int | None = None
) -> ExpenseDB:

    db = Sessionlocal()
    try:
        expense_row = ExpenseDB(
            user_id=user_id,
            amount=expense.amount,
            currency=expense.currency,
            merchant=expense.merchant,
            category=expense.category,
            subcategory=expense.subcategory,
            date=expense.date,
            description=expense.description,
            subscription_id=subscription_id,
        )
        db.add(expense_row)
        db.commit()
        db.refresh(expense_row)

        return expense_row
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_expenses_by_ids(user_id: str, expense_ids: list[int]) -> list[ExpenseResult]:
    db = Sessionlocal()
    try:
        rows = (
            db.query(ExpenseDB)
            .filter(ExpenseDB.user_id == user_id, ExpenseDB.id.in_(expense_ids))
            .order_by(ExpenseDB.date.desc())
            .all()
        )
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
            for r in rows
        ]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_expense(user_id: str, expense_query: ExpenseQuery) -> list[ExpenseResult]:
    db = Sessionlocal()

    try:
        query = db.query(ExpenseDB).filter(ExpenseDB.user_id == user_id)

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

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_expenses(user_id: str, updates: list[ExpenseUpdate]) -> list[ExpenseDB]:

    db = Sessionlocal()

    try:
        updated_expenses = []

        for update in updates:
            expense = (
                db.query(ExpenseDB)
                .filter(ExpenseDB.id == update.expense_id, ExpenseDB.user_id == user_id)
                .first()
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


def delete_expenses(user_id: str, expense_ids: list[int]) -> list[int]:
    db = Sessionlocal()

    try:
        deleted = []
        for eid in expense_ids:
            expense = db.query(ExpenseDB).filter(ExpenseDB.id == eid, ExpenseDB.user_id == user_id).first()
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


def save_subscription(user_id: str, subscriptions: list[SubscriptionCreate]) -> list[SubscriptionDB]:
    db = Sessionlocal()
    try:
        db_subscriptions = [
            SubscriptionDB(
                user_id=user_id,
                merchant=subscription.merchant,
                amount=subscription.amount,
                currency=subscription.currency,
                category=subscription.category,
                subcategory=subscription.subcategory,
                frequency=subscription.frequency,
                next_due_date=subscription.next_due_date,
                is_active=True,
            )
            for subscription in subscriptions
        ]

        db.add_all(db_subscriptions)
        db.commit()
        for subscription in db_subscriptions:
            db.refresh(subscription)

        return db_subscriptions
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_subscription(user_id: str, is_active: bool = True) -> list[SubscriptionResponse]:
    db = Sessionlocal()
    try:
        query = db.query(SubscriptionDB).filter(SubscriptionDB.user_id == user_id)

        if is_active:
            query = query.filter(SubscriptionDB.is_active.is_(True))

        subscriptions = query.order_by(SubscriptionDB.next_due_date).all()

        return [
            SubscriptionResponse(
                id=subscription.id,
                merchant=subscription.merchant,
                amount=subscription.amount,
                currency=subscription.currency,
                category=subscription.category,
                subcategory=subscription.subcategory,
                frequency=subscription.frequency,
                next_due_date=subscription.next_due_date,
                is_active=subscription.is_active,
            )
            for subscription in subscriptions
        ]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_subscriptions(user_id: str, updates: list[SubscriptionUpdate]) -> list[SubscriptionDB]:
    db = Sessionlocal()
    try:
        updated_subscriptions = []
        for update in updates:
            subscription = (
                db.query(SubscriptionDB)
                .filter(SubscriptionDB.id == update.subscription_id, SubscriptionDB.user_id == user_id)
                .first()
            )
            if not subscription:
                continue
            update_data = update.model_dump(
                exclude={"subscription_id"}, exclude_none=True
            )
            for field, value in update_data.items():
                setattr(subscription, field, value)
            updated_subscriptions.append(subscription)
        db.commit()
        for subscription in updated_subscriptions:
            db.refresh(subscription)
        return updated_subscriptions
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_subscriptions(user_id: str, subscription_ids: list[int]) -> list[int]:
    db = Sessionlocal()
    try:
        deleted = []
        for sid in subscription_ids:
            subscription = (
                db.query(SubscriptionDB).filter(SubscriptionDB.id == sid, SubscriptionDB.user_id == user_id).first()
            )
            if subscription:
                db.delete(subscription)
                deleted.append(sid)
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_budget(
    user_id: str, category: ExpenseCategory | None, amount: float, period: str = "monthly"
) -> BudgetDB:
    db = Sessionlocal()
    try:
        existing = (
            db.query(BudgetDB)
            .filter(BudgetDB.user_id == user_id)
            .filter(BudgetDB.category == (category.value if category else None))
            .filter(BudgetDB.period == period)
            .first()
        )
        if existing:
            existing.amount = amount
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_budget = BudgetDB(
                user_id=user_id,
                category=category.value if category else None,
                amount=amount,
                period=period,
            )
            db.add(new_budget)
            db.commit()
            db.refresh(new_budget)
            return new_budget
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_all_budgets(user_id: str) -> list[dict]:
    db = Sessionlocal()
    try:
        budgets = db.query(BudgetDB).filter(BudgetDB.user_id == user_id, BudgetDB.period == "monthly").all()
        return [
            {"id": b.id, "category": b.category, "amount": b.amount, "period": b.period}
            for b in budgets
        ]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_expenses_for_month(
    user_id: str,
    year: int,
    month: int,
    currency: str | None = None
) -> list[ExpenseDB]:
    """Fetch all expenses for a specific month."""
    db = Sessionlocal()
    try:
        query = db.query(ExpenseDB).filter(
            ExpenseDB.user_id == user_id,
            func.extract("year", ExpenseDB.date) == year,
            func.extract("month", ExpenseDB.date) == month
        )
        if currency:
            query = query.filter(ExpenseDB.currency == currency)
        expenses = query.order_by(ExpenseDB.date.desc()).all()
        return expenses
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_budgets_for_period(user_id: str, period: str = "monthly") -> list[BudgetDB]:
    """Fetch all budgets for a given period."""
    db = Sessionlocal()
    try:
        budgets = db.query(BudgetDB).filter(BudgetDB.user_id == user_id, BudgetDB.period == period).all()
        return budgets
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _add_months(current: date, months: int) -> date:
    m = current.month - 1 + months
    year = current.year + m // 12
    month = m % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def advance_due_date(current: date, frequency: str) -> date:
    """Return the next due date after `current` for a given frequency."""
    match frequency:
        case "daily":
            return current + timedelta(days=1)
        case "weekly":
            return current + timedelta(weeks=1)
        case "monthly":
            return _add_months(current, 1)
        case "quarterly":
            return _add_months(current, 3)
        case "yearly":
            return _add_months(current, 12)
        case _:
            return _add_months(current, 1)


def get_due_subscriptions(
    user_id: str, on_or_before: date | None = None
) -> list[SubscriptionResponse]:
    """Active subscriptions due on or before the given date (default: today)."""
    if on_or_before is None:
        on_or_before = date.today()
    db = Sessionlocal()
    try:
        rows = (
            db.query(SubscriptionDB)
            .filter(
                SubscriptionDB.user_id == user_id,
                SubscriptionDB.is_active.is_(True),
                SubscriptionDB.next_due_date <= on_or_before,
            )
            .order_by(SubscriptionDB.next_due_date)
            .all()
        )
        return [
            SubscriptionResponse(
                id=s.id,
                merchant=s.merchant,
                amount=s.amount,
                currency=s.currency,
                category=s.category,
                subcategory=s.subcategory,
                frequency=s.frequency,
                next_due_date=s.next_due_date,
                is_active=s.is_active,
            )
            for s in rows
        ]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_subscriptions_due_within(
    user_id: str, within_days: int = 3
) -> list[SubscriptionResponse]:
    """Active subscriptions due within the next `within_days` days (inclusive of today)."""
    cutoff = date.today() + timedelta(days=within_days)
    db = Sessionlocal()
    try:
        rows = (
            db.query(SubscriptionDB)
            .filter(
                SubscriptionDB.user_id == user_id,
                SubscriptionDB.is_active.is_(True),
                SubscriptionDB.next_due_date <= cutoff,
            )
            .order_by(SubscriptionDB.next_due_date)
            .all()
        )
        return [
            SubscriptionResponse(
                id=s.id,
                merchant=s.merchant,
                amount=s.amount,
                currency=s.currency,
                category=s.category,
                subcategory=s.subcategory,
                frequency=s.frequency,
                next_due_date=s.next_due_date,
                is_active=s.is_active,
            )
            for s in rows
        ]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def advance_subscription_due_date(
    user_id: str, subscription_id: int, new_due_date: date
) -> bool:
    """Update a subscription's next_due_date. Returns True if the row was updated."""
    db = Sessionlocal()
    try:
        row = (
            db.query(SubscriptionDB)
            .filter(
                SubscriptionDB.id == subscription_id,
                SubscriptionDB.user_id == user_id,
            )
            .first()
        )
        if not row:
            return False
        row.next_due_date = new_due_date
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def catch_up_due_date(current_due: date, frequency: str, today: date) -> date:
    """Advance `current_due` by frequency steps until it falls after `today`."""
    new_due = current_due
    guard = 0
    while new_due <= today and guard < 1200:
        new_due = advance_due_date(new_due, frequency)
        guard += 1
    return new_due
