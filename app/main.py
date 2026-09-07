from fastapi import FastAPI
from app.graph.state import ChatRequest, ChatResponse
from langchain_core.messages import HumanMessage
from app.graph.graph import create_expense_graph
from langgraph.types import Command

app = FastAPI()
expense_graph = create_expense_graph()


@app.get("/")
def root():
    return {"message": "Expense Tracker Agent is running"}


@app.get("/health")
async def health():
    return {"status": "Application is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    config = {"configurable": {"thread_id": request.thread_id}}

    # check if convo is already paused
    state_snapshot = expense_graph.get_state(config)

    if state_snapshot.next:
        # graph is paused
        result = expense_graph.invoke(Command(resume=request.message), config=config)

    else:
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "intent": "other",
            "expense": None,
            "validation_result": None,
            "clarification_rounds": 0,
            "response": "",
        }

        result = expense_graph.invoke(initial_state, config=config)

    if "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0]

        return ChatResponse(response=interrupt_data.value)

    return ChatResponse(response=result.get("response", ""))
