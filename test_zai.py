"""Test ZAI GLM model with PydanticAI."""

import os
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent

load_dotenv()

if not os.environ.get("ZAI_API_KEY"):
    print("ERROR: Set ZAI_API_KEY environment variable")
    print("  export ZAI_API_KEY=your_api_key_here")
    exit(1)


class Contact(BaseModel):
    name: str
    email: str


agent = Agent("zai:glm-4.5-flash")
result = agent.run_sync("introduce urself")

print(result)
