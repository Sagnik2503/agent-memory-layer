from app.graph.state import AgentState
from app.llm.model import LLMClient
from app.models.expense import Expense, ValidationResult

llm_client = LLMClient()


def router_node(state: AgentState) -> dict:
    """Classify user message as expense or other."""
    message = state["user_message"]

    try:
        print("Classifying intent...")
        intent = llm_client.classify_intent(message)
        print(f"intent: {intent}")
        return {"intent": intent}

    except Exception as e:
        print(f"Router error: {e}")
        return {"intent": "other"}


def clarification_node(state: AgentState) -> dict:
    """Check if expense has enough info, ask follow-up if not."""
    message = state["user_message"]
    history = state.get("clarification_history", [])
    rounds = state.get("clarification_rounds", 0)

    if rounds >= 3:
        print("Max clarification rounds reached, falling back to extraction")
        return {"intent": "expense"}

    try:
        print("Checking clarity...")
        clarity = llm_client.check_clarity(message, history)
        print(f"clarity check: {clarity}")

        if clarity["is_clear"]:
            return {"intent": "expense"}

        new_history = history + [{"user": message, "assistant": None}]
        return {
            "intent": "needs_clarification",
            "response": clarity["clarification_question"],
            "clarification_history": new_history,
            "clarification_rounds": rounds + 1,
        }

    except Exception as e:
        print(f"Clarity check error: {e}")
        return {"intent": "expense"}


def expense_extractor_node(state: AgentState) -> dict:
    """Extract structured expense from natural language"""
    message = state["user_message"]
    history = state.get("clarification_history", [])

    # Build full context from clarification history
    full_message = message
    if history:
        context_parts = [f"Original: {h['user']}" for h in history if h.get('user')]
        context_parts.append(f"Latest: {message}")
        full_message = " | ".join(context_parts)

    print(f"INPUT TO EXTRACTOR: {full_message}")
    try:
        expense = llm_client.extract_expense(full_message)
        print(f"EXTRACTOR RESULT: {expense}")
        return {"expense": expense, "clarification_history": []}
    except Exception as e:
        print(f"Extraction error: {e}")
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

    if not expense.amount or expense.amount <= 0:
        errors.append("Amount must be greater than 0")
        missing_fields.append("amount")

    if not expense.currency:
        errors.append("Currency is required")
        missing_fields.append("currency")

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
    existing_response = state.get("response", "")

    # If we already have a clarification response, just pass it through
    if intent == "needs_clarification" and existing_response:
        return {}

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
