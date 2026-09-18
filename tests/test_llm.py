from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os

load_dotenv()

llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=os.getenv("OPENAI_API_KEY"),
    use_responses_api=True,
    output_version="responses/v1",
    max_completion_tokens=2000,
)

response = llm.invoke([HumanMessage(content="Say hello")])

print(response)
print("CONTENT:", response.content[-1]["text"])

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from app.agent.tools import tools
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=os.getenv("OPENAI_API_KEY"),
    use_responses_api=True,
)
llm_with_tools = llm.bind_tools(tools)
response = llm_with_tools.invoke([HumanMessage(content="hello")])
print(response.content)
print(response.response_metadata.get("status"))
print(response.usage_metadata)
