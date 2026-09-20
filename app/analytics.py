from datetime import date
from app.agent.state import (
    MonthlySummary,
    CategoryBreakdown,
    BudgetStatus,
    SubscriptionSummary,
    MonthComparison,
    BudgetInput,
    ExpenseResult,
    SubscriptionResponse,
)
from collections import defaultdict


def get_monthly_summary(
    expenses: list[ExpenseResult],
    month: str,  # "2026-09"
    currency: str = "INR"
) -> MonthlySummary:
    """Calculate total spent, transaction count, averages for a month."""
    if not expenses:
        return MonthlySummary(
            month=month,
            total_spent=0.0,
            total_transactions=0,
            average_transaction=0.0,
            top_category="N/A",
            top_merchant="N/A",
            currency=currency,
        )

    total_spent = sum(e.amount for e in expenses)
    total_transactions = len(expenses)
    average_transaction = total_spent / total_transactions if total_transactions > 0 else 0.0

    # Find top category
    category_totals: dict[str, float] = defaultdict(float)
    for e in expenses:
        if e.category:
            category_totals[e.category.value] += e.amount
    top_category = max(category_totals, key=category_totals.get) if category_totals else "N/A"

    # Find top merchant
    merchant_totals: dict[str, float] = defaultdict(float)
    for e in expenses:
        if e.merchant:
            merchant_totals[e.merchant] += e.amount
    top_merchant = max(merchant_totals, key=merchant_totals.get) if merchant_totals else "N/A"

    return MonthlySummary(
        month=month,
        total_spent=total_spent,
        total_transactions=total_transactions,
        average_transaction=average_transaction,
        top_category=top_category,
        top_merchant=top_merchant,
        currency=currency,
    )


def get_category_breakdown(
    expenses: list[ExpenseResult]
) -> list[CategoryBreakdown]:
    """Group expenses by category, calculate totals and percentages."""
    if not expenses:
        return []

    category_totals: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)

    for e in expenses:
        if e.category:
            category_totals[e.category.value] += e.amount
            category_counts[e.category.value] += 1

    total_spent = sum(category_totals.values())
    breakdowns = []

    for category, amount in category_totals.items():
        percentage = (amount / total_spent * 100) if total_spent > 0 else 0.0
        count = category_counts[category]
        avg_per_transaction = amount / count if count > 0 else 0.0

        breakdowns.append(CategoryBreakdown(
            category=category,
            amount=amount,
            percentage=percentage,
            transaction_count=count,
            average_per_transaction=avg_per_transaction,
        ))

    return sorted(breakdowns, key=lambda x: x.amount, reverse=True)


def get_budget_status(
    budgets: list[BudgetInput],
    expenses: list[ExpenseResult],
    month: str
) -> list[BudgetStatus]:
    """Compare budget limits against actual spending for the month."""
    if not budgets:
        return []

    # Calculate spending by category
    category_spending: dict[str, float] = defaultdict(float)
    overall_spending = 0.0

    for e in expenses:
        if e.category:
            category_spending[e.category.value] += e.amount
        overall_spending += e.amount

    statuses = []
    for budget in budgets:
        if budget.category is None:
            # Overall budget
            spent = overall_spending
        else:
            spent = category_spending.get(budget.category, 0.0)

        remaining = budget.amount - spent
        percentage_used = (spent / budget.amount * 100) if budget.amount > 0 else 0.0
        is_over_budget = spent > budget.amount

        statuses.append(BudgetStatus(
            category=budget.category,
            budget_amount=budget.amount,
            spent_amount=spent,
            remaining=remaining,
            percentage_used=percentage_used,
            is_over_budget=is_over_budget,
        ))

    return statuses


def get_subscription_summary(
    subscriptions: list[SubscriptionResponse]
) -> SubscriptionSummary:
    """Aggregate subscription costs, group by category, find next dues."""
    if not subscriptions:
        return SubscriptionSummary(
            total_monthly_cost=0.0,
            active_count=0,
            by_category=[],
            next_due_dates=[],
        )

    active = [s for s in subscriptions if s.is_active]
    total_monthly_cost = sum(float(s.amount) for s in active)

    # Group by category
    category_totals: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    for s in active:
        if s.category:
            category_totals[s.category.value] += float(s.amount)
            category_counts[s.category.value] += 1

    by_category = []
    for category, amount in category_totals.items():
        count = category_counts[category]
        percentage = (amount / total_monthly_cost * 100) if total_monthly_cost > 0 else 0.0
        by_category.append(CategoryBreakdown(
            category=category,
            amount=amount,
            percentage=percentage,
            transaction_count=count,
            average_per_transaction=amount / count if count > 0 else 0.0,
        ))

    # Get next due dates
    next_due_dates = [
        {"merchant": s.merchant, "amount": float(s.amount), "due_date": s.next_due_date.isoformat()}
        for s in sorted(active, key=lambda x: x.next_due_date)[:5]
    ]

    return SubscriptionSummary(
        total_monthly_cost=total_monthly_cost,
        active_count=len(active),
        by_category=sorted(by_category, key=lambda x: x.amount, reverse=True),
        next_due_dates=next_due_dates,
    )


def compare_months(
    current: MonthlySummary,
    previous: MonthlySummary
) -> MonthComparison:
    """Calculate month-over-month changes and trends."""
    total_change = current.total_spent - previous.total_spent
    total_change_percentage = (
        (total_change / previous.total_spent * 100) if previous.total_spent > 0 else 0.0
    )

    top_category_change = {
        "category": current.top_category,
        "change_amount": 0.0,
        "change_percentage": 0.0,
    }

    return MonthComparison(
        current_month=current,
        previous_month=previous,
        total_change=total_change,
        total_change_percentage=total_change_percentage,
        top_category_change=top_category_change,
    )


def get_spending_by_merchant(
    expenses: list[ExpenseResult],
    top_n: int = 5
) -> list[dict]:
    """Get top merchants by spending amount."""
    if not expenses:
        return []

    merchant_totals: dict[str, float] = defaultdict(float)
    for e in expenses:
        if e.merchant:
            merchant_totals[e.merchant] += e.amount

    sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return [
        {"merchant": merchant, "total_spent": amount}
        for merchant, amount in sorted_merchants
    ]
