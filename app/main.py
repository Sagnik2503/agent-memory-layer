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
    # Initialize state
    initial_state = {
        "user_message": request.message,
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": "",
    }

    # Run the graph
    result = expense_graph.invoke(initial_state)

    return ChatResponse(response=result["response"])
