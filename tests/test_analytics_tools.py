import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from app.agent.tools import (
    get_monthly_summary_tool,
    get_category_breakdown_tool,
    get_budget_status_tool,
    get_subscription_summary_tool,
    compare_months_tool,
    get_spending_by_merchant_tool,
)
from app.agent.state import (
    MonthlySummary,
    CategoryBreakdown,
    BudgetStatus,
    SubscriptionSummary,
    MonthComparison,
)


@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_monthly_summary")
def test_monthly_summary_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = MonthlySummary(
        month="2026-09", total_spent=0.0, total_transactions=0,
        average_transaction=0.0, top_category="N/A",
        top_merchant="N/A", currency="INR"
    )
    
    result = get_monthly_summary_tool.invoke({"month": "2026-09", "currency": "INR"})
    
    assert isinstance(result, MonthlySummary)
    mock_repo.assert_called_once_with(2026, 9, "INR")


@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_category_breakdown")
def test_category_breakdown_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = []
    
    result = get_category_breakdown_tool.invoke({"month": "2026-09", "currency": "INR"})
    
    assert isinstance(result, list)
    mock_repo.assert_called_once_with(2026, 9, "INR")


@patch("app.agent.tools.get_budgets_for_period")
@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_budget_status")
def test_budget_status_tool(mock_analytics, mock_expenses, mock_budgets):
    mock_budgets.return_value = []
    mock_expenses.return_value = []
    mock_analytics.return_value = []
    
    result = get_budget_status_tool.invoke({})
    
    assert isinstance(result, list)


@patch("app.agent.tools.get_subscription")
@patch("app.agent.tools.get_subscription_summary")
def test_subscription_summary_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = SubscriptionSummary(
        total_monthly_cost=0.0, active_count=0,
        by_category=[], next_due_dates=[]
    )
    
    result = get_subscription_summary_tool.invoke({})
    
    assert isinstance(result, SubscriptionSummary)


@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_monthly_summary")
def test_compare_months_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = MonthlySummary(
        month="2026-09", total_spent=0.0, total_transactions=0,
        average_transaction=0.0, top_category="N/A",
        top_merchant="N/A", currency="INR"
    )
    
    result = compare_months_tool.invoke({"month1": "2026-09", "month2": "2026-08"})
    
    assert isinstance(result, MonthComparison)


@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_spending_by_merchant")
def test_spending_by_merchant_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = []
    
    result = get_spending_by_merchant_tool.invoke({"month": "2026-09", "top_n": 5})
    
    assert isinstance(result, list)
