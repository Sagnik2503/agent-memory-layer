from app.db.database import Sessionlocal
from app.db.models import ExpenseDB, SubscriptionDB
from app.agent.state import (
    ExpenseInput,
    ExpenseQuery,
    ExpenseResult,
    ExpenseUpdate,
    SubscriptionResponse,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionDelete,
)
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


def save_subscription(subscriptions: list[SubscriptionCreate]) -> list[SubscriptionDB]:
    db = Sessionlocal()
    try:
        db_subscriptions = [
            SubscriptionDB(
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

    finally:
        db.close()


def get_subscription(is_active: bool = True) -> SubscriptionResponse:
    db = Sessionlocal()
    try:
        query = db.query(SubscriptionDB)

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
    finally:
        db.close()


def update_subscriptions(updates: list[SubscriptionUpdate]) -> list[SubscriptionDB]:
    db = Sessionlocal()
    try:
        updated_subscriptions = []
        for update in updates:
            subscription = (
                db.query(SubscriptionDB)
                .filter(SubscriptionDB.id == update.subscription_id)
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


def delete_subscriptions(subscription_ids: list[int]) -> list[int]:
    db = Sessionlocal()
    try:
        deleted = []
        for sid in subscription_ids:
            subscription = (
                db.query(SubscriptionDB).filter(SubscriptionDB.id == sid).first()
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
