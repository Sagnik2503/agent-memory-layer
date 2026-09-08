from app.graph.state import AgentState, Expense, ValidationResult
from app.llm.model import LLMClient
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage
from app.db.repository import save_expense, get_expense

llm_client = LLMClient()


def router_node(state: AgentState) -> dict:
    """Classify user message as expense or other."""
    user_message = state["messages"][-1].content

    try:
        print("Classifying intent...")
        result = llm_client.classify_intent(user_message)
        print(f"intent: {result.intent}, confidence: {result.confidence}")
        return {"intent": result.intent}

    except Exception as e:
        print(f"Router error: {e}")
        return {"intent": "other"}


def extract_query_node(state: AgentState) -> AgentState:
    """extracts information for expense retrieval"""
    query = state["messages"][-1].content

    try:
        extracted_query_result = llm_client.extract_query(query)
        if extracted_query_result is not None:
            return {"expense_query": extracted_query_result}
    except Exception as e:
        print(f"could not extract user query: {e}")
    return {"expense_query": None}


def execute_query_node(state: AgentState) -> AgentState:
    """fetches the data from the db based on the query"""
    expense_query = state["expense_query"]
    try:
        results = get_expense(expense_query)
        return {"query_results": results}
    except Exception as e:
        print(f"Could not retrieve expenses: {e}")
        return {"query_results": []}


def format_query_node(state: AgentState) -> dict:
    """Format database results into a natural-language response."""

    query_results = state["query_results"]
    user_query = state["messages"][-1].content

    if not query_results:
        return {"query_response": "No expenses found matching your criteria."}

    try:
        response = llm_client.format_query(
            user_query=user_query, query_results=query_results
        )

        return {"query_response": response}

    except Exception as e:
        print(f"Could not format query response: {e}")

        return {"query_response": "Sorry, I couldn't format the expense results."}


def expense_extractor_node(state: AgentState) -> dict:
    """Extract structured expense from natural language"""
    user_message = state["messages"][-1].content

    print(f"INPUT TO EXTRACTOR: {user_message}")

    try:
        expense = llm_client.extract_expense(user_message)
        print(f"EXTRACTOR RESULT: {expense}")

        return {"expense": expense}

    except Exception as e:
        print(f"Extraction error: {e}")

        return {"expense": None}


def validate_expense_node(state: AgentState) -> dict:
    """Validate extracted expense data"""
    expense = state.get("expense")

    if expense is None:
        return {
            "validation_result": ValidationResult(
                is_valid=False,
                errors=["No expense data provided"],
                missing_fields=["amount", "currency", "category"],
            )
        }

    errors: list[str] = []
    missing_fields: list[str] = []

    # Amount
    if expense.amount is None:
        missing_fields.append("amount")
    elif expense.amount <= 0:
        errors.append("Amount must be greater than 0")

    # currenct
    if not expense.currency:
        errors.append("Currency is required")
        missing_fields.append("currency")

    # cateogry
    if not expense.category:
        errors.append("Category is required")
        missing_fields.append("category")

    is_valid = not errors and not missing_fields

    return {
        "validation_result": ValidationResult(
            is_valid=is_valid,
            errors=errors,
            missing_fields=missing_fields,
        )
    }


def route_after_validation(state: AgentState) -> AgentState:
    """routing logic after validation has been done for clarification"""

    validation_results = state["validation_result"]

    if validation_results["is_valid"]:
        return "save"
    if validation_results.missing_fields:
        return "clarification"
    return "response"


def clarification_node(state: AgentState) -> dict:
    """Check if expense has enough info, ask follow-up if not."""

    rounds = state.get("clarification_rounds", 0)
    validation_results = state["validation_result"]

    if validation_results is None:
        return {"response": "I could not validate the expense"}

    if rounds >= 3:
        return {
            "response": (
                "I'm missing some information to complete this expense. "
                "Please provide the expense with all the required details."
            )
        }

    missing_fields = validation_results.missing_fields

    if not missing_fields:
        return {}

    field = missing_fields[0]

    questions = {
        "amount": "How much did you spend?",
        "currency": "What currency was the expense in?",
        "category": "What category should I use for this expense?",
        "merchant": "Where did you make this purchase?",
        "date": "What date was this expense?",
    }

    question = questions.get(field, f"Could you provide the {field}?")

    print(f"Clarification needed for: {field}")
    print(f"Question: {question}")

    answer = interrupt(question)

    return {
        "messages": [HumanMessage(content=answer)],
        "clarification_rounds": rounds + 1,
    }


def merge_clarification_node(state: AgentState) -> dict:
    expense = state["expense"]
    validation = state["validation_result"]

    if not expense or not validation:
        return {}

    answer = state["messages"][-1].content
    field = validation.missing_fields[0]

    try:
        updated_expense = llm_client.merge_clarification(
            expense=expense,
            missing_field=field,
            user_answer=answer,
        )

        return {"expense": updated_expense}

    except Exception as e:
        print(f"Clarification merge error: {e}")
        return {}


def save_expense_node(state: AgentState) -> AgentState:
    """saves the expense to the db"""
    expense = state["expense"]

    try:
        save_expense(expense)
    except Exception as e:
        print(f"Could not save the expense: {e}")


def response_node(state: AgentState) -> dict:
    """Generate natural language response based on state"""
    intent = state.get("intent")
    expense = state.get("expense")

    validation_result = state.get("validation_result")
    existing_response = state.get("response", "")
    query_response = state.get("query_response", "")

    if intent == "other":
        return {"response": "I'm ready to help you track and understand your spending."}

    if intent == "expense":
        if not expense:
            return {"response": "I couldn't extract expense details."}

        merchant = f" at {expense.merchant}" if expense.merchant else ""
        category = f" under {expense.category}" if expense.category else ""

        return {
            "response": (
                f"Got it — ₹{expense.amount} spent"
                f"{merchant}{category}. Record saved successfully"
            )
        }

    if intent == "query":
        if query_response:
            return {"response": query_response}
        return {"response": "I couldn't retrieve your expenses."}

    return {"response": "I'm not sure how to help with that."}
