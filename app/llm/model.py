import os
from dotenv import load_dotenv
from pydantic import BaseModel
import instructor
from openai import OpenAI
from app.graph.state import Expense, IntentClassification, ExpenseQuery
from datetime import date

load_dotenv()


class FormatResponse(BaseModel):
    response: str


INTENT_PROMPT = """Classify the user's message into exactly one of these intents:

1. "expense"
- The user is reporting a NEW expense or describing money they have spent.
- Examples:
    - "I spent ₹500 on lunch"
    - "I paid $20 for Uber"
    - "Bought coffee for 200 rupees"
    - "I spent 1000 on groceries yesterday"

2. "query"
- The user wants to retrieve, view, analyze, or ask about EXISTING expenses.
- Examples:
    - "What did I spend yesterday?"
    - "Show me my expenses from the last 2 days"
    - "How much did I spend last month?"
    - "List all my restaurant expenses"
    - "What was my biggest expense?"

3. "other"
- The message is unrelated to recording or retrieving expenses.
- Examples:
    - "Hello"
    - "How are you?"
    - "What can you do?"
    - "Tell me a joke"
    - "What's the weather today?"

Important rules:
- Use "expense" only when the user is describing a NEW expense to be recorded.
- Use "query" when the user is asking about expenses that already exist.
- Use "other" for everything unrelated to recording or querying expenses.
- Return exactly one intent: "expense", "query", or "other"."""


QUERY_PROMPT = """You are an expense-query parser.
Extract the user's intent into the provided ExpenseQuery structure.

Today's date is {current_date}.

Convert natural-language time expressions into explicit start_date and end_date values.

Examples:
- "yesterday" → start_date = yesterday, end_date = yesterday
- "last 2 days" → start_date = 2 days before today, end_date = today
- "last 7 days" → start_date = 7 days before today, end_date = today
- "this month" → start_date = first day of the current month, end_date = today
- "last month" → start_date = first day of the previous month, end_date = last day of the previous month
- "expenses at Petercat" → merchant = "Petercat"
- "food expenses last month" → category = "food", start_date = first day of previous month, end_date = last day of previous month

Determine the appropriate aggregation:
- "list" when the user wants to see individual expenses
- "total" when the user asks how much they spent
- "count" when the user asks how many expenses they had

Do not invent filters that are not present or implied in the user's query."""


FORMAT_PROMPT = """You are a helpful expense tracking assistant.

The user asked:
{user_query}

The database returned the following expenses:
{query_results}

Generate a clear, concise, natural-language response to the user.

Instructions:
- Answer the user's question directly.
- Use only the information present in the database results.
- Do not invent or assume missing information.
- If the user asks for a total, calculate the total from the returned expenses.
- If multiple categories, merchants, or other groups are relevant, provide a useful breakdown.
- If the user asks to list expenses, present them as a readable bullet list.
- Mention the date range when it helps clarify the answer.
- Include the currency with monetary amounts.
- If there are no matching expenses, clearly tell the user that no expenses were found.
- Keep the response concise and easy to read.

Return only the response that should be shown to the user."""


EXPENSE_PROMPT = """Extract expense information from this user message.
Today's date is: {today}"""


MERGE_PROMPT = """Update the existing expense using the user's clarification.

Existing expense:
{expense}

Missing field:
{missing_field}

User's clarification:
{user_answer}

Update only the missing field(s) that can be confidently
extracted from the user's clarification. Preserve all existing
values."""


class LLMClient:
    def __init__(self):
        self.model = "Qwen/Qwen3-32B"
        hf_token = os.getenv("HF_TOKEN")
        
        raw_client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
        )
        
        self.client = instructor.from_openai(
            raw_client,
            mode=instructor.Mode.JSON,
        )

    def classify_intent(self, message: str) -> IntentClassification:
        """Classify user message as 'expense', 'query', or 'other'"""
        return self.client.chat.completions.create(
            model=self.model,
            response_model=IntentClassification,
            messages=[{"role": "user", "content": f"{INTENT_PROMPT}\n\nUser message:\n{message}"}],
        )

    def extract_query(self, message: str) -> ExpenseQuery:
        """Extract query information from user input"""
        current_date = date.today().isoformat()
        prompt = QUERY_PROMPT.format(current_date=current_date)
        return self.client.chat.completions.create(
            model=self.model,
            response_model=ExpenseQuery,
            messages=[{"role": "user", "content": f"{prompt}\n\nUser query:\n{message}"}],
        )

    def format_query(self, user_query, query_results) -> str:
        """Format query results into natural language response"""
        formatted_results = [
            {
                "amount": r.amount,
                "currency": r.currency,
                "merchant": r.merchant,
                "category": r.category,
                "subcategory": r.subcategory,
                "date": r.date,
                "description": r.description,
            }
            for r in query_results
        ]
        prompt = FORMAT_PROMPT.format(
            user_query=user_query, query_results=formatted_results
        )
        result = self.client.chat.completions.create(
            model=self.model,
            response_model=FormatResponse,
            messages=[{"role": "user", "content": prompt}],
        )
        return result.response

    def merge_clarification(
        self,
        expense: Expense,
        missing_field: str,
        user_answer: str,
    ) -> Expense:
        """Merge user clarification into existing expense"""
        prompt = MERGE_PROMPT.format(
            expense=expense.model_dump(),
            missing_field=missing_field,
            user_answer=user_answer,
        )
        return self.client.chat.completions.create(
            model=self.model,
            response_model=Expense,
            messages=[{"role": "user", "content": prompt}],
        )

    def extract_expense(self, message: str) -> Expense:
        """Extract structured expense from natural language"""
        today = date.today().isoformat()
        prompt = EXPENSE_PROMPT.format(today=today)
        return self.client.chat.completions.create(
            model=self.model,
            response_model=Expense,
            messages=[{"role": "user", "content": f"{prompt}\n\nUser message: {message}"}],
        )
