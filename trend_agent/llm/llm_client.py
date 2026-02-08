from openai import OpenAI
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import OPENAI_API_KEY, MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


async def call_llm(prompt):
    """
    Call OpenAI API with a given prompt.

    Args:
        prompt: The prompt to send to the LLM

    Returns:
        LLM's response text
    """
    response = client.chat.completions.create(
        model=MODEL, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
