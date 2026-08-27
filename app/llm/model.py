import os
import instructor
from dotenv import load_dotenv
from app.models.expense import Expense, ClarityCheck
from datetime import date

load_dotenv()


class LLMClient:
    def __init__(self):
        self.client = instructor.from_provider(
            "groq/openai/gpt-oss-20b",
            api_key=os.environ["GROQ_API_KEY"],
        )
        self.model = "groq/openai/gpt-oss-20b"

    def classify_intent(self, message: str) -> str:
        """Classify user message as 'expense' or 'other'"""
        prompt = f"""
        Classify this user message as either "expense" or "other".
        Expense messages describe spending money on something (e.g., "I spent ₹500 on lunch").
        Other messages are questions, greetings, or non-expense requests.

        User message: {message}

        Respond with ONLY the classification: "expense" or "other"
        """

        result = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=str,
        )

        return "expense" if "expense" in result.lower() else "other"

    def check_clarity(self, message: str, history: list[dict] = None) -> dict:
        """Check if the message has enough info to extract an expense."""
        history_text = ""
        if history:
            history_text = "\nPrevious conversation:\n" + "\n".join(
                f"User: {h['user']}"
                + (f"\nAssistant: {h['assistant']}" if h.get("assistant") else "")
                for h in history
            )

        prompt = f"""
        You are checking if a user message contains enough information to extract an expense.
        Required fields: amount (how much was spent), currency (e.g. INR, USD), and category (e.g. food, transport).
        Optional fields: merchant, date, subcategory, description.

        Analyze the user message and determine:
        1. Is there enough information to extract at least amount, currency, and category?
        2. What fields are missing?
        3. What follow-up question should be asked to get the missing info?

        Be smart about inference:
        - If someone says "rupees" or "₹", currency is INR
        - If someone says "dollars" or "$", currency is USD
        - If someone mentions a restaurant/food place, category is likely "food"
        - If someone mentions a taxi/uber/bus, category is likely "transport"
        - If the amount is mentioned, even without explicit currency, it may be inferable from context
        {history_text}
        User message: {message}
        """

        result = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=ClarityCheck,
        )

        return {
            "is_clear": result.is_clear,
            "missing_fields": result.missing_fields,
            "clarification_question": result.clarification_question,
        }

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
