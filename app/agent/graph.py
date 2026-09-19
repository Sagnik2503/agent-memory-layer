from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.agent.tools import tools
from app.agent.prompts import SYSTEM_PROMPT
from dotenv import load_dotenv

load_dotenv()

import os

llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=os.getenv("OPENAI_API_KEY"),
    use_responses_api=True,
    output_version="responses/v1",
    max_completion_tokens=2000,
)
llm_with_tools = llm.bind_tools(tools)


def extract_text(content) -> str:
    """Pull plain text out of a Responses API content list, without mutating it."""
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if b.get("type") == "text")


def agent_node(state: AgentState):
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    try:
        response = llm_with_tools.invoke(messages)
        for tc in response.tool_calls:
            print(f"[tool call] {tc['name']} {tc['args']}")
        return {"messages": [response]}
    except Exception as e:
        print(f"[error] {e}")
        error_response = AIMessage(
            content="I encountered an error processing your request. Please try again."
        )
        return {"messages": [error_response]}


def create_agent_graph():
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

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/agent_state.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return builder.compile(checkpointer=checkpointer)


graph = create_agent_graph()


def main():
    config = {"configurable": {"thread_id": "local-user"}}
    while True:
        try:
            user = input("\nuser: ")
            if user == "exit":
                break
            result = graph.invoke(
                {"messages": [HumanMessage(content=user)]},
                config=config,
            )
            ai_message = result["messages"][-1]
            print(f"assistant: {extract_text(ai_message.content)}")
        except KeyboardInterrupt:
            print("\nShutting down.")
            break
        except Exception as e:
            print(f"[error] An unexpected error occurred. Please try again.")
            continue


if __name__ == "__main__":
    main()
