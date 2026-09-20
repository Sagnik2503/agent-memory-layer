# Analytics Service Design

**Date:** 2026-09-20  
**Status:** Approved  
**Author:** opencode  

## Overview

Add an analytics layer to the expense tracking agent that provides structured data for the LLM to present to users. The service performs all calculations, ensuring accuracy and preventing LLM hallucination of financial data.

## Target User

Individual users tracking personal finances.

## Architecture

**Approach:** Separate Analytics Service Layer

```
Repository (DB queries) → Analytics Service (calculations) → Tools (LLM interface)
```

**Rationale:**
- Clean separation of concerns
- Easy to test analytics logic independently
- Can evolve analytics without touching CRUD operations
- Keeps tools thin and focused on orchestration

## Data Models

```python
# Monthly Summary
class MonthlySummary(BaseModel):
    month: str  # "2026-09"
    total_spent: float
    total_transactions: int
    average_transaction: float
    top_category: str
    top_merchant: str
    currency: str

# Category Breakdown
class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int
    average_per_transaction: float

# Budget Status
class BudgetStatus(BaseModel):
    category: str | None  # None = overall budget
    budget_amount: float
    spent_amount: float
    remaining: float
    percentage_used: float
    is_over_budget: bool

# Subscription Summary
class SubscriptionSummary(BaseModel):
    total_monthly_cost: float
    active_count: int
    by_category: list[CategoryBreakdown]
    next_due_dates: list[dict]  # {merchant, amount, due_date}

# Month-over-Month Comparison
class MonthComparison(BaseModel):
    current_month: MonthlySummary
    previous_month: MonthlySummary
    total_change: float
    total_change_percentage: float
    top_category_change: dict  # {category, change_amount, change_percentage}

# Budget Input (for analytics)
class BudgetInput(BaseModel):
    category: str | None  # None = overall budget
    amount: float
    period: str  # "monthly"
```

## Analytics Service Functions

```python
def get_monthly_summary(
    expenses: list[ExpenseResult],
    month: str,  # "2026-09"
    currency: str = "INR"
) -> MonthlySummary:
    """Calculate total spent, transaction count, averages for a month."""

def get_category_breakdown(
    expenses: list[ExpenseResult]
) -> list[CategoryBreakdown]:
    """Group expenses by category, calculate totals and percentages."""

def get_budget_status(
    budgets: list[BudgetInput],
    expenses: list[ExpenseResult],
    month: str
) -> list[BudgetStatus]:
    """Compare budget limits against actual spending for the month."""

def get_subscription_summary(
    subscriptions: list[SubscriptionResponse]
) -> SubscriptionSummary:
    """Aggregate subscription costs, group by category, find next dues."""

def compare_months(
    current: MonthlySummary,
    previous: MonthlySummary
) -> MonthComparison:
    """Calculate month-over-month changes and trends."""

def get_spending_by_merchant(
    expenses: list[ExpenseResult],
    top_n: int = 5
) -> list[dict]:
    """Get top merchants by spending amount."""
```

**Key design decisions:**
- Functions accept database results as input (no direct DB access)
- Return structured Pydantic models
- Stateless and easily testable
- Currency conversion handled at input layer

## Repository Layer Additions

```python
def get_expenses_for_month(
    year: int,
    month: int,
    currency: str | None = None
) -> list[ExpenseDB]:
    """Fetch all expenses for a specific month."""

def get_budgets_for_period(
    period: str = "monthly"
) -> list[BudgetDB]:
    """Fetch all budgets for a given period."""
```

## Analytics Tools

```python
@tool
def get_monthly_summary_tool(
    month: str | None = None,  # Defaults to current month
    currency: str = "INR"
) -> MonthlySummary:
    """Get spending summary for a specific month.
    
    Use when user asks: 'How much did I spend this month?', 'Monthly summary', 'What's my spending for September?'
    """

@tool
def get_category_breakdown_tool(
    month: str | None = None,
    currency: str = "INR"
) -> list[CategoryBreakdown]:
    """Get spending breakdown by category.
    
    Use when user asks: 'Where did I spend the most?', 'Show category breakdown', 'What categories am I spending on?'
    """

@tool
def get_budget_status_tool() -> list[BudgetStatus]:
    """Get status of all budgets vs actual spending.
    
    Use when user asks: 'How am I doing on my budgets?', 'Am I over budget?', 'Budget status'
    """

@tool
def get_subscription_summary_tool() -> SubscriptionSummary:
    """Get summary of all active subscriptions.
    
    Use when user asks: 'How much am I spending on subscriptions?', 'Subscription summary', 'What are my recurring costs?'
    """

@tool
def compare_months_tool(
    month1: str,  # "2026-09"
    month2: str   # "2026-08"
) -> MonthComparison:
    """Compare spending between two months.
    
    Use when user asks: 'Compare this month to last month', 'How does September compare to August?'
    """

@tool
def get_spending_by_merchant_tool(
    month: str | None = None,
    top_n: int = 5
) -> list[dict]:
    """Get top merchants by spending.
    
    Use when user asks: 'Where do I spend the most?', 'Top merchants', 'Biggest expenses'
    """
```

**Tool registration:**
```python
tools = [
    # Existing CRUD tools...
    # New analytics tools
    get_monthly_summary_tool,
    get_category_breakdown_tool,
    get_budget_status_tool,
    get_subscription_summary_tool,
    compare_months_tool,
    get_spending_by_merchant_tool,
]
```

## Prompt Updates

```python
SYSTEM_PROMPT = f"""
You are a conversational AI personal finance assistant.

Today's date is {date.today().isoformat()}.

You help users manage expenses, subscriptions, budgets, and spending insights.

Rules:
- Use tools for all database operations.
- Never fabricate financial data. Treat tool results as the source of truth.
- Use existing tool results before updating or deleting records.
- Ask for clarification when required information is missing or ambiguous.
- Ask only for information that is actually required.
- Preserve context across turns and use information already provided.
- Handle multiple items in a single request when possible.
- If some items are incomplete, ask only about the missing information.
- Interpret natural-language dates such as "today", "yesterday", and "this month" correctly.
- Historical expenses must not be changed automatically when a subscription or budget changes.
- Calculate financial summaries and insights from actual database results.
- Never expose internal tools, database details, or implementation details.
- Keep responses concise and natural.

Analytics Guidelines:
- When users ask about spending patterns, trends, or summaries, use the analytics tools.
- Present numbers in a conversational way, not as raw data.
- Compare to previous periods when relevant (e.g., "You spent 15% more on food this month").
- Highlight notable changes or anomalies without being asked.
- Use the structured data from analytics tools to provide accurate insights.
"""
```

## Testing Strategy

**Unit tests for analytics service:**

```python
# tests/test_analytics.py

def test_get_monthly_summary_basic():
    """Test monthly summary with sample expenses."""

def test_get_monthly_summary_empty_month():
    """Test monthly summary when no expenses exist."""

def test_get_category_breakdown():
    """Test category breakdown calculations."""

def test_get_budget_status_on_track():
    """Test budget status when under budget."""

def test_get_budget_status_over_budget():
    """Test budget status when over budget."""

def test_get_subscription_summary():
    """Test subscription aggregation."""

def test_compare_months_increase():
    """Test month comparison when spending increased."""

def test_compare_months_decrease():
    """Test month comparison when spending decreased."""

def test_get_spending_by_merchant():
    """Test top merchants calculation."""
```

**Integration tests for tools:**

```python
# tests/test_analytics_tools.py

def test_monthly_summary_tool():
    """Test tool returns valid MonthlySummary."""

def test_category_breakdown_tool():
    """Test tool returns valid CategoryBreakdown list."""

def test_budget_status_tool():
    """Test tool returns valid BudgetStatus list."""
```

## Implementation Order

1. Add Pydantic models to `state.py`
2. Add repository query functions
3. Create `analytics.py` service
4. Add analytics tools to `tools.py`
5. Update system prompt
6. Write unit tests
7. Write integration tests
8. Manual testing with sample data

## Files to Modify

- `app/agent/state.py` - Add analytics models
- `app/db/repository.py` - Add query functions
- `app/agent/tools.py` - Add analytics tools
- `app/agent/prompts.py` - Update system prompt

## Files to Create

- `app/analytics.py` - Analytics service
- `tests/test_analytics.py` - Unit tests
- `tests/test_analytics_tools.py` - Integration tests
