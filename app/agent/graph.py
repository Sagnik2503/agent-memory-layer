from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.state import AgentState
from app.agent.tools import tools
from app.agent.prompts import SYSTEM_PROMPT
from dotenv import load_dotenv

load_dotenv()

import os

llm = ChatOpenAI(
    model="Qwen/Qwen3-32B",
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_TOKEN"),
    max_tokens=1024,
)

llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState):

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")

builder.add_conditional_edges(
    "agent",
    tools_condition,
    {
        "tools": "tools",
        "__end__": END,
    },
)

builder.add_edge("tools", "agent")

graph = builder.compile()


def main():
    messages = []
    while True:
        user = input("user:")
        if user == "exit":
            break
        messages.append(HumanMessage(content=user))
        result = graph.invoke({"messages": messages})
        ai_message = result["messages"][-1]
        messages.append(ai_message)

        print("assistant:", ai_message.content)


if __name__ == "__main__":
    main()
