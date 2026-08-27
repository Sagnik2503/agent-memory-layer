from fastapi import FastAPI
from app.models.chat import ChatRequest, ChatResponse
from app.graph.graph import create_expense_graph

app = FastAPI()
expense_graph = create_expense_graph()


@app.get("/")
def root():
    return {"message": "Expense Tracker Agent is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    history = [msg.model_dump() for msg in request.clarification_history] if request.clarification_history else []
    initial_state = {
        "user_message": request.message,
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": "",
        "clarification_history": history,
        "clarification_rounds": request.clarification_rounds,
    }

    result = expense_graph.invoke(initial_state)

    return ChatResponse(
        response=result["response"],
        needs_clarification=result.get("intent") == "needs_clarification",
        clarification_history=result.get("clarification_history", []),
        clarification_rounds=result.get("clarification_rounds", 0),
    )
