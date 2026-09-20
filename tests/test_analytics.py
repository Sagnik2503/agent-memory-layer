import pytest
from datetime import date
from app.analytics import (
    get_monthly_summary,
    get_category_breakdown,
    get_budget_status,
    get_subscription_summary,
    compare_months,
    get_spending_by_merchant,
)
from app.agent.state import (
    MonthlySummary,
    CategoryBreakdown,
    BudgetStatus,
    SubscriptionSummary,
    MonthComparison,
    BudgetInput,
    ExpenseResult,
    SubscriptionResponse,
    ExpenseCategory,
    SubscriptionFrequency,
)


@pytest.fixture
def sample_expenses():
    return [
        ExpenseResult(
            id=1, amount=500.0, currency="INR", merchant="Swiggy",
            category=ExpenseCategory.FOOD, subcategory="delivery",
            date=date(2026, 9, 1), description="lunch"
        ),
        ExpenseResult(
            id=2, amount=200.0, currency="INR", merchant="Uber",
            category=ExpenseCategory.TRANSPORT, subcategory="ride",
            date=date(2026, 9, 5), description="commute"
        ),
        ExpenseResult(
            id=3, amount=300.0, currency="INR", merchant="Swiggy",
            category=ExpenseCategory.FOOD, subcategory="dinner",
            date=date(2026, 9, 10), description="dinner"
        ),
        ExpenseResult(
            id=4, amount=150.0, currency="INR", merchant="Amazon",
            category=ExpenseCategory.SHOPPING, subcategory="electronics",
            date=date(2026, 9, 15), description="charger"
        ),
    ]


@pytest.fixture
def sample_subscriptions():
    return [
        SubscriptionResponse(
            id=1, merchant="Netflix", amount=649.0, currency="INR",
            category=ExpenseCategory.ENTERTAINMENT, subcategory=None,
            frequency=SubscriptionFrequency.MONTHLY, next_due_date=date(2026, 10, 1),
            is_active=True
        ),
        SubscriptionResponse(
            id=2, merchant="Spotify", amount=199.0, currency="INR",
            category=ExpenseCategory.ENTERTAINMENT, subcategory="music",
            frequency=SubscriptionFrequency.MONTHLY, next_due_date=date(2026, 10, 5),
            is_active=True
        ),
        SubscriptionResponse(
            id=3, merchant="Gym", amount=2000.0, currency="INR",
            category=ExpenseCategory.HEALTH, subcategory="fitness",
            frequency=SubscriptionFrequency.MONTHLY, next_due_date=date(2026, 10, 1),
            is_active=True
        ),
    ]


@pytest.fixture
def sample_budgets():
    return [
        BudgetInput(category=None, amount=10000.0, period="monthly"),
        BudgetInput(category="food", amount=3000.0, period="monthly"),
    ]


def test_get_monthly_summary_basic(sample_expenses):
    summary = get_monthly_summary(sample_expenses, "2026-09", "INR")

    assert summary.month == "2026-09"
    assert summary.total_spent == 1150.0
    assert summary.total_transactions == 4
    assert summary.average_transaction == 287.5
    assert summary.top_category == "food"
    assert summary.top_merchant == "Swiggy"
    assert summary.currency == "INR"


def test_get_monthly_summary_empty_month():
    summary = get_monthly_summary([], "2026-01", "INR")

    assert summary.month == "2026-01"
    assert summary.total_spent == 0.0
    assert summary.total_transactions == 0
    assert summary.average_transaction == 0.0
    assert summary.top_category == "N/A"
    assert summary.top_merchant == "N/A"


def test_get_category_breakdown(sample_expenses):
    breakdown = get_category_breakdown(sample_expenses)

    assert len(breakdown) == 3
    assert breakdown[0].category == "food"
    assert breakdown[0].amount == 800.0
    assert breakdown[0].transaction_count == 2
    assert breakdown[1].category == "transport"
    assert breakdown[1].amount == 200.0
    assert breakdown[2].category == "shopping"
    assert breakdown[2].amount == 150.0


def test_get_budget_status_on_track(sample_budgets, sample_expenses):
    statuses = get_budget_status(sample_budgets, sample_expenses)

    assert len(statuses) == 2

    overall = next(s for s in statuses if s.category is None)
    assert overall.budget_amount == 10000.0
    assert overall.spent_amount == 1150.0
    assert overall.remaining == 8850.0
    assert overall.percentage_used == pytest.approx(11.5)
    assert overall.is_over_budget is False

    food = next(s for s in statuses if s.category == "food")
    assert food.budget_amount == 3000.0
    assert food.spent_amount == 800.0
    assert food.remaining == 2200.0
    assert food.is_over_budget is False


def test_get_budget_status_over_budget():
    budgets = [BudgetInput(category="food", amount=500.0, period="monthly")]
    expenses = [
        ExpenseResult(
            id=1, amount=600.0, currency="INR", merchant="Restaurant",
            category=ExpenseCategory.FOOD, subcategory=None,
            date=date(2026, 9, 1), description="dinner"
        )
    ]

    statuses = get_budget_status(budgets, expenses)

    assert len(statuses) == 1
    assert statuses[0].is_over_budget is True
    assert statuses[0].remaining == -100.0
    assert statuses[0].percentage_used == pytest.approx(120.0)


def test_get_subscription_summary(sample_subscriptions):
    summary = get_subscription_summary(sample_subscriptions)

    assert summary.total_monthly_cost == 2848.0
    assert summary.active_count == 3
    assert len(summary.by_category) == 2
    assert len(summary.next_due_dates) == 3


def test_compare_months():
    current = MonthlySummary(
        month="2026-09", total_spent=1500.0, total_transactions=10,
        average_transaction=150.0, top_category="food",
        top_merchant="Swiggy", currency="INR"
    )
    previous = MonthlySummary(
        month="2026-08", total_spent=1200.0, total_transactions=8,
        average_transaction=150.0, top_category="transport",
        top_merchant="Uber", currency="INR"
    )

    comparison = compare_months(current, previous)

    assert comparison.total_change == 300.0
    assert comparison.total_change_percentage == pytest.approx(25.0)
    assert comparison.current_month == current
    assert comparison.previous_month == previous


def test_get_spending_by_merchant(sample_expenses):
    merchants = get_spending_by_merchant(sample_expenses, top_n=2)

    assert len(merchants) == 2
    assert merchants[0]["merchant"] == "Swiggy"
    assert merchants[0]["total_spent"] == 800.0
    assert merchants[1]["merchant"] == "Uber"
    assert merchants[1]["total_spent"] == 200.0
