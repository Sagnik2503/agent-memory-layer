# Analytics Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an analytics layer to the expense tracking agent that provides structured data for the LLM to present to users.

**Architecture:** Separate Analytics Service Layer with Repository → Analytics Service → Tools flow. All calculations happen in the service layer, returning structured Pydantic models for the LLM to present conversationally.

**Tech Stack:** Python, SQLAlchemy, Pydantic, LangChain/LangGraph

---

## File Structure

| File | Responsibility |
|------|----------------|
| `app/agent/state.py` | Add analytics Pydantic models |
| `app/db/repository.py` | Add query functions for analytics |
| `app/analytics.py` | **NEW** - Analytics service with calculation functions |
| `app/agent/tools.py` | Add analytics tools |
| `app/agent/prompts.py` | Update system prompt with analytics guidelines |
| `tests/test_analytics.py` | **NEW** - Unit tests for analytics service |
| `tests/test_analytics_tools.py` | **NEW** - Integration tests for analytics tools |

---

### Task 1: Add Analytics Pydantic Models

**Files:**
- Modify: `app/agent/state.py`

- [ ] **Step 1: Add analytics models to state.py**

Add the following models after the existing `CreateSubscriptionsInput` class:

```python
class MonthlySummary(BaseModel):
    month: str  # "2026-09"
    total_spent: float
    total_transactions: int
    average_transaction: float
    top_category: str
    top_merchant: str
    currency: str


class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int
    average_per_transaction: float


class BudgetStatus(BaseModel):
    category: str | None  # None = overall budget
    budget_amount: float
    spent_amount: float
    remaining: float
    percentage_used: float
    is_over_budget: bool


class SubscriptionSummary(BaseModel):
    total_monthly_cost: float
    active_count: int
    by_category: list[CategoryBreakdown]
    next_due_dates: list[dict]  # {merchant, amount, due_date}


class MonthComparison(BaseModel):
    current_month: MonthlySummary
    previous_month: MonthlySummary
    total_change: float
    total_change_percentage: float
    top_category_change: dict  # {category, change_amount, change_percentage}


class BudgetInput(BaseModel):
    category: str | None  # None = overall budget
    amount: float
    period: str  # "monthly"
```

- [ ] **Step 2: Verify models import correctly**

Run: `python -c "from app.agent.state import MonthlySummary, CategoryBreakdown, BudgetStatus, SubscriptionSummary, MonthComparison, BudgetInput; print('All models imported successfully')"`

- [ ] **Step 3: Commit**

```bash
git add app/agent/state.py
git commit -m "feat: add analytics Pydantic models to state.py"
```

---

### Task 2: Add Repository Query Functions

**Files:**
- Modify: `app/db/repository.py`

- [ ] **Step 1: Add get_expenses_for_month function**

Add after the `get_all_budgets` function:

```python
def get_expenses_for_month(
    year: int,
    month: int,
    currency: str | None = None
) -> list[ExpenseDB]:
    """Fetch all expenses for a specific month."""
    db = Sessionlocal()
    try:
        query = db.query(ExpenseDB).filter(
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
```

- [ ] **Step 2: Add get_budgets_for_period function**

Add after the `get_expenses_for_month` function:

```python
def get_budgets_for_period(period: str = "monthly") -> list[BudgetDB]:
    """Fetch all budgets for a given period."""
    db = Sessionlocal()
    try:
        budgets = db.query(BudgetDB).filter(BudgetDB.period == period).all()
        return budgets
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- [ ] **Step 3: Verify functions work**

Run: `python -c "from app.db.repository import get_expenses_for_month, get_budgets_for_period; print('Repository functions imported successfully')"`

- [ ] **Step 4: Commit**

```bash
git add app/db/repository.py
git commit -m "feat: add repository query functions for analytics"
```

---

### Task 3: Create Analytics Service

**Files:**
- Create: `app/analytics.py`

- [ ] **Step 1: Create analytics.py with get_monthly_summary function**

Create `app/analytics.py`:

```python
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
```

- [ ] **Step 2: Add get_category_breakdown function**

Add to `app/analytics.py`:

```python
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
```

- [ ] **Step 3: Add get_budget_status function**

Add to `app/analytics.py`:

```python
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
```

- [ ] **Step 4: Add get_subscription_summary function**

Add to `app/analytics.py`:

```python
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
```

- [ ] **Step 5: Add compare_months function**

Add to `app/analytics.py`:

```python
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
```

- [ ] **Step 6: Add get_spending_by_merchant function**

Add to `app/analytics.py`:

```python
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
```

- [ ] **Step 7: Verify analytics module imports**

Run: `python -c "from app.analytics import get_monthly_summary, get_category_breakdown, get_budget_status, get_subscription_summary, compare_months, get_spending_by_merchant; print('All analytics functions imported successfully')"`

- [ ] **Step 8: Commit**

```bash
git add app/analytics.py
git commit -m "feat: create analytics service with calculation functions"
```

---

### Task 4: Add Analytics Tools

**Files:**
- Modify: `app/agent/tools.py`

- [ ] **Step 1: Add imports to tools.py**

Add to existing imports at the top of `app/agent/tools.py`:

```python
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
)
from app.db.repository import get_expenses_for_month, get_budgets_for_period, get_subscription
from datetime import date
```

- [ ] **Step 2: Add get_monthly_summary_tool**

Add to `app/agent/tools.py`:

```python
@tool
def get_monthly_summary_tool(
    month: str | None = None,
    currency: str = "INR"
) -> MonthlySummary:
    """Get spending summary for a specific month.
    
    Use when user asks: 'How much did I spend this month?', 'Monthly summary', 'What's my spending for September?'
    """
    try:
        if month is None:
            month = date.today().strftime("%Y-%m")
        
        year, month_num = map(int, month.split("-"))
        expenses = get_expenses_for_month(year, month_num, currency)
        
        expense_results = [
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
        
        summary = get_monthly_summary(expense_results, month, currency)
        print(f"[tool output] Monthly summary: {summary.total_spent} total spent")
        return summary
    except Exception as e:
        result = f"Error getting monthly summary: {e}"
        print(f"[tool output] {result}")
        return result
```

- [ ] **Step 3: Add get_category_breakdown_tool**

Add to `app/agent/tools.py`:

```python
@tool
def get_category_breakdown_tool(
    month: str | None = None,
    currency: str = "INR"
) -> list[CategoryBreakdown]:
    """Get spending breakdown by category.
    
    Use when user asks: 'Where did I spend the most?', 'Show category breakdown', 'What categories am I spending on?'
    """
    try:
        if month is None:
            month = date.today().strftime("%Y-%m")
        
        year, month_num = map(int, month.split("-"))
        expenses = get_expenses_for_month(year, month_num, currency)
        
        expense_results = [
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
        
        breakdown = get_category_breakdown(expense_results)
        print(f"[tool output] {len(breakdown)} categories found")
        return breakdown
    except Exception as e:
        result = f"Error getting category breakdown: {e}"
        print(f"[tool output] {result}")
        return []
```

- [ ] **Step 4: Add get_budget_status_tool**

Add to `app/agent/tools.py`:

```python
@tool
def get_budget_status_tool() -> list[BudgetStatus]:
    """Get status of all budgets vs actual spending.
    
    Use when user asks: 'How am I doing on my budgets?', 'Am I over budget?', 'Budget status'
    """
    try:
        today = date.today()
        month = today.strftime("%Y-%m")
        
        budgets_db = get_budgets_for_period("monthly")
        budgets = [
            BudgetInput(
                category=b.category,
                amount=b.amount,
                period=b.period,
            )
            for b in budgets_db
        ]
        
        expenses = get_expenses_for_month(today.year, today.month)
        
        expense_results = [
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
        
        status = get_budget_status(budgets, expense_results, month)
        print(f"[tool output] {len(status)} budgets checked")
        return status
    except Exception as e:
        result = f"Error getting budget status: {e}"
        print(f"[tool output] {result}")
        return []
```

- [ ] **Step 5: Add get_subscription_summary_tool**

Add to `app/agent/tools.py`:

```python
@tool
def get_subscription_summary_tool() -> SubscriptionSummary:
    """Get summary of all active subscriptions.
    
    Use when user asks: 'How much am I spending on subscriptions?', 'Subscription summary', 'What are my recurring costs?'
    """
    try:
        subscriptions = get_subscription(active_only=True)
        summary = get_subscription_summary(subscriptions)
        print(f"[tool output] {summary.active_count} active subscriptions, {summary.total_monthly_cost} monthly cost")
        return summary
    except Exception as e:
        result = f"Error getting subscription summary: {e}"
        print(f"[tool output] {result}")
        return result
```

- [ ] **Step 6: Add compare_months_tool**

Add to `app/agent/tools.py`:

```python
@tool
def compare_months_tool(
    month1: str,
    month2: str
) -> MonthComparison:
    """Compare spending between two months.
    
    Use when user asks: 'Compare this month to last month', 'How does September compare to August?'
    """
    try:
        # Get month 1 data
        year1, month_num1 = map(int, month1.split("-"))
        expenses1 = get_expenses_for_month(year1, month_num1)
        expense_results1 = [
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
            for e in expenses1
        ]
        summary1 = get_monthly_summary(expense_results1, month1)
        
        # Get month 2 data
        year2, month_num2 = map(int, month2.split("-"))
        expenses2 = get_expenses_for_month(year2, month_num2)
        expense_results2 = [
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
            for e in expenses2
        ]
        summary2 = get_monthly_summary(expense_results2, month2)
        
        comparison = compare_months(summary1, summary2)
        print(f"[tool output] Comparison: {comparison.total_change} change ({comparison.total_change_percentage}%)")
        return comparison
    except Exception as e:
        result = f"Error comparing months: {e}"
        print(f"[tool output] {result}")
        return result
```

- [ ] **Step 7: Add get_spending_by_merchant_tool**

Add to `app/agent/tools.py`:

```python
@tool
def get_spending_by_merchant_tool(
    month: str | None = None,
    top_n: int = 5
) -> list[dict]:
    """Get top merchants by spending.
    
    Use when user asks: 'Where do I spend the most?', 'Top merchants', 'Biggest expenses'
    """
    try:
        if month is None:
            month = date.today().strftime("%Y-%m")
        
        year, month_num = map(int, month.split("-"))
        expenses = get_expenses_for_month(year, month_num)
        
        expense_results = [
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
        
        merchants = get_spending_by_merchant(expense_results, top_n)
        print(f"[tool output] {len(merchants)} top merchants found")
        return merchants
    except Exception as e:
        result = f"Error getting spending by merchant: {e}"
        print(f"[tool output] {result}")
        return []
```

- [ ] **Step 8: Update tools list**

Update the `tools` list at the bottom of `app/agent/tools.py`:

```python
tools = [
    create_expenses_tool,
    get_expenses_tool,
    update_expenses_tool,
    delete_expenses_tool,
    get_subscription_tool,
    create_subscription_tool,
    update_subscription_tool,
    delete_subscription_tool,
    set_budget_tool,
    get_budgets_tool,
    get_monthly_summary_tool,
    get_category_breakdown_tool,
    get_budget_status_tool,
    get_subscription_summary_tool,
    compare_months_tool,
    get_spending_by_merchant_tool,
]
```

- [ ] **Step 9: Verify tools import**

Run: `python -c "from app.agent.tools import tools; print(f'{len(tools)} tools imported successfully')"`

- [ ] **Step 10: Commit**

```bash
git add app/agent/tools.py
git commit -m "feat: add analytics tools for spending insights"
```

---

### Task 5: Update System Prompt

**Files:**
- Modify: `app/agent/prompts.py`

- [ ] **Step 1: Add analytics guidelines to system prompt**

Update `SYSTEM_PROMPT` in `app/agent/prompts.py`:

```python
from datetime import date

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

- [ ] **Step 2: Commit**

```bash
git add app/agent/prompts.py
git commit -m "feat: add analytics guidelines to system prompt"
```

---

### Task 6: Write Unit Tests for Analytics Service

**Files:**
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Create test_analytics.py with test fixtures**

Create `tests/test_analytics.py`:

```python
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
```

- [ ] **Step 2: Add test_get_monthly_summary_basic**

Add to `tests/test_analytics.py`:

```python
def test_get_monthly_summary_basic(sample_expenses):
    summary = get_monthly_summary(sample_expenses, "2026-09", "INR")
    
    assert summary.month == "2026-09"
    assert summary.total_spent == 1150.0
    assert summary.total_transactions == 4
    assert summary.average_transaction == 287.5
    assert summary.top_category == "food"
    assert summary.top_merchant == "Swiggy"
    assert summary.currency == "INR"
```

- [ ] **Step 3: Add test_get_monthly_summary_empty_month**

Add to `tests/test_analytics.py`:

```python
def test_get_monthly_summary_empty_month():
    summary = get_monthly_summary([], "2026-01", "INR")
    
    assert summary.month == "2026-01"
    assert summary.total_spent == 0.0
    assert summary.total_transactions == 0
    assert summary.average_transaction == 0.0
    assert summary.top_category == "N/A"
    assert summary.top_merchant == "N/A"
```

- [ ] **Step 4: Add test_get_category_breakdown**

Add to `tests/test_analytics.py`:

```python
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
```

- [ ] **Step 5: Add test_get_budget_status_on_track**

Add to `tests/test_analytics.py`:

```python
def test_get_budget_status_on_track(sample_budgets, sample_expenses):
    statuses = get_budget_status(sample_budgets, sample_expenses, "2026-09")
    
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
```

- [ ] **Step 6: Add test_get_budget_status_over_budget**

Add to `tests/test_analytics.py`:

```python
def test_get_budget_status_over_budget():
    budgets = [BudgetInput(category="food", amount=500.0, period="monthly")]
    expenses = [
        ExpenseResult(
            id=1, amount=600.0, currency="INR", merchant="Restaurant",
            category=ExpenseCategory.FOOD, subcategory=None,
            date=date(2026, 9, 1), description="dinner"
        )
    ]
    
    statuses = get_budget_status(budgets, expenses, "2026-09")
    
    assert len(statuses) == 1
    assert statuses[0].is_over_budget is True
    assert statuses[0].remaining == -100.0
    assert statuses[0].percentage_used == pytest.approx(120.0)
```

- [ ] **Step 7: Add test_get_subscription_summary**

Add to `tests/test_analytics.py`:

```python
def test_get_subscription_summary(sample_subscriptions):
    summary = get_subscription_summary(sample_subscriptions)
    
    assert summary.total_monthly_cost == 2848.0
    assert summary.active_count == 3
    assert len(summary.by_category) == 2
    assert len(summary.next_due_dates) == 3
```

- [ ] **Step 8: Add test_compare_months**

Add to `tests/test_analytics.py`:

```python
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
```

- [ ] **Step 9: Add test_get_spending_by_merchant**

Add to `tests/test_analytics.py`:

```python
def test_get_spending_by_merchant(sample_expenses):
    merchants = get_spending_by_merchant(sample_expenses, top_n=2)
    
    assert len(merchants) == 2
    assert merchants[0]["merchant"] == "Swiggy"
    assert merchants[0]["total_spent"] == 800.0
    assert merchants[1]["merchant"] == "Uber"
    assert merchants[1]["total_spent"] == 200.0
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `pytest tests/test_analytics.py -v`

- [ ] **Step 11: Commit**

```bash
git add tests/test_analytics.py
git commit -m "test: add unit tests for analytics service"
```

---

### Task 7: Write Integration Tests for Analytics Tools

**Files:**
- Create: `tests/test_analytics_tools.py`

- [ ] **Step 1: Create test_analytics_tools.py**

Create `tests/test_analytics_tools.py`:

```python
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
    
    result = get_monthly_summary_tool(month="2026-09", currency="INR")
    
    assert isinstance(result, MonthlySummary)
    mock_repo.assert_called_once_with(2026, 9, "INR")


@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_category_breakdown")
def test_category_breakdown_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = []
    
    result = get_category_breakdown_tool(month="2026-09", currency="INR")
    
    assert isinstance(result, list)
    mock_repo.assert_called_once_with(2026, 9, "INR")


@patch("app.agent.tools.get_budgets_for_period")
@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_budget_status")
def test_budget_status_tool(mock_analytics, mock_expenses, mock_budgets):
    mock_budgets.return_value = []
    mock_expenses.return_value = []
    mock_analytics.return_value = []
    
    result = get_budget_status_tool()
    
    assert isinstance(result, list)


@patch("app.agent.tools.get_subscription")
@patch("app.agent.tools.get_subscription_summary")
def test_subscription_summary_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = SubscriptionSummary(
        total_monthly_cost=0.0, active_count=0,
        by_category=[], next_due_dates=[]
    )
    
    result = get_subscription_summary_tool()
    
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
    
    result = compare_months_tool(month1="2026-09", month2="2026-08")
    
    assert isinstance(result, MonthComparison)


@patch("app.agent.tools.get_expenses_for_month")
@patch("app.agent.tools.get_spending_by_merchant")
def test_spending_by_merchant_tool(mock_analytics, mock_repo):
    mock_repo.return_value = []
    mock_analytics.return_value = []
    
    result = get_spending_by_merchant_tool(month="2026-09", top_n=5)
    
    assert isinstance(result, list)
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_analytics_tools.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/test_analytics_tools.py
git commit -m "test: add integration tests for analytics tools"
```

---

### Task 8: Manual Testing

- [ ] **Step 1: Start the agent**

Run: `python -m app.agent.graph`

- [ ] **Step 2: Test monthly summary**

Send: "How much did I spend this month?"

Expected: Agent calls `get_monthly_summary_tool` and returns a conversational summary.

- [ ] **Step 3: Test category breakdown**

Send: "Where did I spend the most?"

Expected: Agent calls `get_category_breakdown_tool` and returns category breakdown.

- [ ] **Step 4: Test budget status**

Send: "How am I doing on my budgets?"

Expected: Agent calls `get_budget_status_tool` and returns budget status.

- [ ] **Step 5: Test subscription summary**

Send: "How much am I spending on subscriptions?"

Expected: Agent calls `get_subscription_summary_tool` and returns subscription summary.

- [ ] **Step 6: Test month comparison**

Send: "Compare this month to last month"

Expected: Agent calls `compare_months_tool` and returns comparison.

- [ ] **Step 7: Test merchant spending**

Send: "Where do I spend the most?"

Expected: Agent calls `get_spending_by_merchant_tool` and returns top merchants.

- [ ] **Step 8: Commit all changes**

```bash
git add -A
git commit -m "feat: complete analytics service implementation"
```
