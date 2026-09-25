from fastapi import FastAPI, HTTPException
from app.agent.state import ChatRequest, ChatResponse
from langchain_core.messages import HumanMessage
from app.agent.graph import create_agent_graph
from app.config import DEFAULT_USER_ID
from app.db.database import Base, engine
from app.db.migrations import migrate_add_user_id
from sqlalchemy.exc import SQLAlchemyError


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        migrate_add_user_id(engine, DEFAULT_USER_ID)
    except SQLAlchemyError as e:
        print(f"[error] Failed to initialize database: {e}")


app = FastAPI()

init_db()

try:
    expense_graph = create_agent_graph()
except Exception as e:
    print(f"[error] Failed to create agent graph: {e}")
    expense_graph = None


@app.get("/")
def root():
    return {"message": "Expense Tracker Agent is running"}


@app.get("/health")
async def health():
    return {"status": "Application is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if expense_graph is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        config = {
            "configurable": {
                "thread_id": request.thread_id,
                "user_id": request.user_id or DEFAULT_USER_ID,
            }
        }

        result = expense_graph.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )

        ai_message = result["messages"][-1]

        if isinstance(ai_message.content, list):
            text_parts = [
                b["text"] for b in ai_message.content if b.get("type") == "text"
            ]
            return ChatResponse(response="\n".join(text_parts))

        return ChatResponse(response=ai_message.content)
    except Exception as e:
        print(f"[error] Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat message")
