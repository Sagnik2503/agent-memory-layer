import os
import instructor
from dotenv import load_dotenv
from app.models.expense import Expense

load_dotenv()


class LLMClient:
    def __init__(self):
        self.client = instructor.from_provider(
            "openai/nvidia/nemotron-3-ultra-550b-a55b:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def classify_intent(self, message: str) -> str:
        """Classify user message as 'expense' or 'other'"""
        prompt = f"""
        Classify this user message as either "expense" or "other".
        Expense messages describe spending money (e.g., "I spent ₹500 on lunch").
        Other messages are questions, greetings, or non-expense requests.
        
        User message: {message}
        
        Respond with ONLY the classification: "expense" or "other"
        """

        result = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=str,
        )

        return "expense" if "expense" in result.lower() else "other"

    def extract_expense(self, message: str) -> Expense:
        """Extract structured expense from natural language"""
        prompt = f"""
        Extract expense information from this user message.
        
        User message: {message}
        """

        expense = self.client.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=Expense,
        )
        return expense
