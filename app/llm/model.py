import os
import instructor
from dotenv import load_dotenv
from pydantic import BaseModel
from app.graph.state import Expense, IntentClassification, ExpenseQuery
from langchain_core.messages import AnyMessage

from datetime import date

load_dotenv()


class LLMClient:
    def __init__(self):
        self.model = "google/gemini-3.6-flash"
        self.client = instructor.from_provider(
            self.model,
            api_key=os.environ["GEMINI_API_KEY"],
            mode=instructor.Mode.JSON,
        )

    def classify_intent(self, message: str) -> IntentClassification:
        """Classify user message as 'expense' or 'other'"""
        prompt = f"""
            Classify the user's message into exactly one of these intents:

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
            - Return exactly one intent: "expense", "query", or "other".

            User message:
            {message}
        """

        result = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=IntentClassification,
        )

        return result

    def extract_query(self, message: str) -> ExpenseQuery:
        """extracts query information from user input"""

        current_date = date.today().isoformat()

        prompt = f"""
            You are an expense-query parser.

            Extract the user's intent into the provided ExpenseQuery structure.

            Today's date is {current_date}.

            Your job is to convert natural-language time expressions into explicit
            start_date and end_date values.

            Examples:

            - "yesterday"
            → start_date = yesterday
            → end_date = yesterday

            - "last 2 days"
            → start_date = 2 days before today
            → end_date = today

            - "last 7 days"
            → start_date = 7 days before today
            → end_date = today

            - "this month"
            → start_date = first day of the current month
            → end_date = today

            - "last month"
            → start_date = first day of the previous month
            → end_date = last day of the previous month

            - "expenses at Petercat"
            → merchant = "Petercat"

            - "food expenses last month"
            → category = "food"
            → start_date = first day of previous month
            → end_date = last day of previous month

            Determine the appropriate aggregation:
            - "list" when the user wants to see individual expenses
            - "total" when the user asks how much they spent
            - "count" when the user asks how many expenses they had

            Do not invent filters that are not present or implied in the user's query.

            User query:
            {message}"""

        return self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=ExpenseQuery,
        )

    def format_query(self, user_query, query_results) -> str:

        formatted_query_result = [
            {
                "amount": results.amount,
                "currency": results.currency,
                "merchant": results.merchant,
                "category": results.category,
                "subcategory": results.subcategory,
                "date": results.date,
                "description": results.description,
            }
            for results in query_results
        ]
        prompt = f"""
            You are a helpful expense tracking assistant.

            The user asked:
            {user_query}

            The database returned the following expenses:
            {formatted_query_result}

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

            Return only the response that should be shown to the user.
            """

        class FormatResponse(BaseModel):
            response: str

        formatted_message = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=FormatResponse,
        )

        return formatted_message.response

    def merge_clarification(
        self,
        expense: Expense,
        missing_field: str,
        user_answer: str,
    ) -> Expense:

        prompt = f"""
        Update the existing expense using the user's clarification.

        Existing expense:
        {expense.model_dump()}

        Missing field:
        {missing_field}

        User's clarification:
        {user_answer}

        Update only the missing field(s) that can be confidently
        extracted from the user's clarification. Preserve all existing
        values.
        """

        return self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=Expense,
        )

    def extract_expense(self, message: str) -> Expense:
        """Extract structured expense from natural language using instructor"""
        today = date.today().isoformat()
        prompt = f"""
        Extract expense information from this user message.
        Today's date is: {today}
        User message: {message}
        """

        expense = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=Expense,
        )

        return expense
