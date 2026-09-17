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
    model="gpt-5-nano",
    api_key=os.getenv("OPENAI_API_KEY"),
    use_responses_api=True,
    output_version="responses/v1",
)
llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState):
    print(f"\n[agent] {len(state['messages'])} message(s)")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    try:
        response = llm_with_tools.invoke(messages)
        if isinstance(response.content, list):
            text_parts = [
                b["text"] for b in response.content if b.get("type") == "text"
            ]
            response.content = "\n".join(text_parts)
        if response.tool_calls:
            for tc in response.tool_calls:
                print(f"[tool call] {tc['name']} {tc['args']}")
        if response.content:
            print(f"[response] {response.content[:300]}")
        return {"messages": [response]}
    except Exception as e:
        print(f"[error] {e}")
        from langchain_core.messages import AIMessage

        error_response = AIMessage(content=f"Error processing request: {e}")
        return {"messages": [error_response]}


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
        try:
            user = input("\nuser: ")
            if user == "exit":
                break
            messages.append(HumanMessage(content=user))
            result = graph.invoke({"messages": messages})
            ai_message = result["messages"][-1]
            messages.append(ai_message)
            print(f"assistant: {ai_message.content}")
        except KeyboardInterrupt:
            print("\nShutting down.")
            break
        except Exception as e:
            print(f"[error] {e}")
            continue


if __name__ == "__main__":
    main()
