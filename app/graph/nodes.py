from app.graph.state import AgentState
from app.llm.model import LLMClient
from app.models.expense import Expense, ValidationResult

llm_client = LLMClient()


def router_node(state: AgentState) -> dict:
    """Classify user message as 'expense' or 'other'"""
    message = state["user_message"]

    try:
        print("Classifying intent...\n\n")
        intent = llm_client.classify_intent(message)
        print(f"intent: {intent}\n\n")
        return {"intent": intent}
    except Exception as e:
        # Fallback: simple keyword matching
        expense_keywords = ["spent", "paid", "bought", "cost", "rupees", "₹"]
        if any(keyword in message.lower() for keyword in expense_keywords):
            return {"intent": "expense"}
        return {"intent": "other"}


def expense_extractor_node(state: AgentState) -> dict:
    """Extract structured expense from natural language"""
    message = state["user_message"]
    print("INPUT TO EXTRACTOR:", message)
    try:
        expense = llm_client.extract_expense(message)
        print("EXTRACTOR RESULT:", expense)
        return {"expense": expense}
    except Exception as e:
        return {"expense": None}


def validate_expense_node(state: AgentState) -> dict:
    """Validate extracted expense data"""
    expense = state.get("expense")

    if not expense:
        return {
            "validation_result": ValidationResult(
                is_valid=False,
                errors=["No expense data provided"],
                missing_fields=["amount", "currency", "category"],
            )
        }

    errors = []
    missing_fields = []

    # Validate amount
    if not expense.amount or expense.amount <= 0:
        errors.append("Amount must be greater than 0")
        missing_fields.append("amount")

    # Validate currency
    if not expense.currency:
        errors.append("Currency is required")
        missing_fields.append("currency")

    # Validate category
    if not expense.category:
        errors.append("Category is required")
        missing_fields.append("category")

    return {
        "validation_result": ValidationResult(
            is_valid=len(errors) == 0, errors=errors, missing_fields=missing_fields
        )
    }


def response_node(state: AgentState) -> dict:
    """Generate natural language response based on state"""
    intent = state.get("intent")
    expense = state.get("expense")
    validation_result = state.get("validation_result")

    if intent == "other":
        return {"response": "I'm ready to help you track and understand your spending."}

    if intent == "expense":
        if not expense:
            return {
                "response": "I couldn't extract expense details. Could you provide more information?"
            }

        if validation_result and not validation_result.is_valid:
            missing = (
                validation_result.missing_fields[0]
                if validation_result.missing_fields
                else "details"
            )
            return {
                "response": f"How much did you spend on {expense.description or 'this'}?"
            }

        merchant_part = f" at {expense.merchant}" if expense.merchant else ""
        category_part = f" under {expense.category}" if expense.category else ""
        return {
            "response": f"Got it — ₹{expense.amount} spent{merchant_part}{category_part}."
        }

    return {"response": "I'm not sure how to help with that."}
