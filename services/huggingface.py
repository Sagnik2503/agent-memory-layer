import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_TOKEN"),
)


def call_huggingface(
    message: str, model: str = "Qwen/Qwen3.8-2.4T-A95B:together"
) -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": message}],
    )
    return completion.choices[0].message.content
