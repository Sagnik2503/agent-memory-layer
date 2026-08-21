from fastapi import FastAPI
from models.chat import ChatRequest, ChatResponse
from services.huggingface import call_huggingface

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    response = call_huggingface(request.message)
    return ChatResponse(response=response)
