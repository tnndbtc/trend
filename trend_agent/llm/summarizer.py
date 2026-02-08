from .llm_client import call_llm


async def summarize(cluster):
    """
    Generate a summary for a cluster of related topics.

    Args:
        cluster: List of Topic objects

    Returns:
        Summary text from LLM
    """
    text = "\n".join([t.title for t in cluster])

    prompt = f"""You are a professional trend analyst.

Summarize the following cluster into:
- Trend title
- 3 bullet key points
- 2 sentence explanation

Text:
{text}
"""

    return await call_llm(prompt)
