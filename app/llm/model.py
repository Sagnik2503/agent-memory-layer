import os
import instructor
from dotenv import load_dotenv
from app.graph.state import Expense, IntentClassification
from langchain_core.messages import AnyMessage

from datetime import date

load_dotenv()


class LLMClient:
    def __init__(self):
        self.client = instructor.from_provider(
            "groq/openai/gpt-oss-20b",
            api_key=os.environ["GROQ_API_KEY"],
        )
        self.model = "groq/openai/gpt-oss-20b"

    def classify_intent(self, message: str) -> IntentClassification:
        """Classify user message as 'expense' or 'other'"""
        prompt = f"""
        Classify this user message as either "expense" or "other".
        Expense messages describe spending money on something (e.g., "I spent ₹500 on lunch").
        Other messages are questions, greetings, or non-expense requests.

        User message: {message}
        """

        result = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=IntentClassification,
        )

        return result

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
