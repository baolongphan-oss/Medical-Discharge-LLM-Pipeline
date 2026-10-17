# src/llm.py
import os, time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL_NAME = os.environ.get("LLM_MODEL")
client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL"),
    api_key=os.environ.get("GROQ_API_KEY"),
)

def call_with_retry(messages, json_mode=False, max_attempts=3):
    kwargs = {"model": MODEL_NAME, "temperature": 0, "messages": messages}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for a in range(max_attempts):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError:
            wait = 10 * (a + 1)
            print(f"Rate limited, waiting {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Still rate limited after {max_attempts} retries.")