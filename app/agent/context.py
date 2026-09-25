from datetime import date
from app.db.repository import (
    get_subscriptions_due_within,
    get_budgets_for_period,
    get_expenses_for_month,
)
from app.analytics import get_budget_status
from app.agent.state import BudgetInput, ExpenseResult


def _expense_results(expenses) -> list[ExpenseResult]:
    return [
        ExpenseResult(
            id=e.id,
            amount=e.amount,
            currency=e.currency,
            merchant=e.merchant,
            category=e.category,
            subcategory=e.subcategory,
            date=e.date,
            description=e.description,
        )
        for e in expenses
    ]


def build_proactive_context(user_id: str) -> str:
    """Short block of time-sensitive facts (due bills, budget alerts) for the system prompt.

    Never raises: failures degrade to an empty string.
    """
    lines: list[str] = []
    today = date.today()

    try:
        due = get_subscriptions_due_within(user_id, within_days=3)
        if due:
            lines.append("Due soon / overdue subscriptions (mention proactively when relevant):")
            for s in due:
                if s.next_due_date < today:
                    when = f"OVERDUE since {s.next_due_date}"
                elif s.next_due_date == today:
                    when = "due today"
                else:
                    when = f"due {s.next_due_date}"
                lines.append(
                    f"- {s.merchant}: {s.currency} {float(s.amount):,.2f} ({when})"
                )
    except Exception:
        pass

    try:
        budgets_db = get_budgets_for_period(user_id, "monthly")
        if budgets_db:
            budgets = [
                BudgetInput(category=b.category, amount=b.amount, period=b.period)
                for b in budgets_db
            ]
            expenses = _expense_results(
                get_expenses_for_month(user_id, today.year, today.month)
            )
            for status in get_budget_status(budgets, expenses):
                label = status.category or "overall"
                if status.is_over_budget:
                    over = status.spent_amount - status.budget_amount
                    lines.append(
                        f"BUDGET EXCEEDED [{label}]: spent {status.spent_amount:,.2f} "
                        f"of {status.budget_amount:,.2f} ({over:,.2f} over). "
                        "Surface this to the user naturally; never block recording an expense."
                    )
                elif status.percentage_used >= 80:
                    lines.append(
                        f"BUDGET WARNING [{label}]: {status.percentage_used:.0f}% used "
                        f"({status.spent_amount:,.2f} of {status.budget_amount:,.2f})."
                    )
    except Exception:
        pass

    return "\n".join(lines)
