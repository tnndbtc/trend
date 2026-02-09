from .llm_client import call_llm, call_llm_json
import json


async def summarize_topics_batch(topics):
    """
    Generate summaries for multiple topics in a single API call (batch processing).

    Args:
        topics: List of Topic objects

    Returns:
        List of dicts with title_summary and full_summary for each topic
    """
    # Build input array
    topics_data = []
    for t in topics:
        content = t.content if t.content else t.description if t.description else ""
        topics_data.append({
            "title": t.title,
            "url": t.url,
            "content": content,
            "language": t.language
        })

    prompt = f"""You are an AI agent that processes trending posts from social media and news sources.
Process these {len(topics)} topics and return a JSON array with summaries.

Input topics:
{json.dumps(topics_data, indent=2)}

For EACH topic, generate:
1. title_summary: A concise summary using around 15 words, preserving the core meaning
2. full_summary: MUST start with "[URL] Original Title: " then provide a brief content summary

CRITICAL FORMAT for full_summary:
"[{{url}}] {{original_title}}: Brief summary of the content here"

Example:
{{
  "title_summary": "New AI model achieves breakthrough in reasoning tasks",
  "full_summary": "[https://example.com/post] Original Post Title: Researchers announce a new AI model that shows significant improvements in logical reasoning and problem-solving capabilities."
}}

Output MUST be a JSON array with exactly {len(topics)} objects:
[
  {{
    "title_summary": "...",
    "full_summary": "[URL] Title: ..."
  }},
  ...
]

Important:
- Generate summaries for ALL {len(topics)} topics
- Preserve the original language where appropriate
- Keep title_summary around 15 words
- ALWAYS include the [URL] and original title in full_summary
- Do not invent facts; summarize only provided content
"""

    try:
        # Use higher token limit for batch processing (approx 100 tokens per topic)
        max_tokens = min(4000, len(topics) * 150)
        result = await call_llm_json(prompt, max_tokens=max_tokens)

        # Ensure result is an array
        if isinstance(result, dict) and 'summaries' in result:
            return result['summaries']
        elif isinstance(result, list):
            return result
        else:
            # Fallback: return empty summaries
            return [{"title_summary": t.title, "full_summary": f"[{t.url}] {t.title}"} for t in topics]

    except Exception as e:
        print(f"Batch summarization error: {e}")
        # Fallback: return basic summaries
        return [{"title_summary": t.title, "full_summary": f"[{t.url}] {t.title}"} for t in topics]


async def summarize_single_topic(topic):
    """
    Generate a summary for a single topic using the docs/todo.txt specification.

    Args:
        topic: Topic object with title, url, content, and language fields

    Returns:
        Dict with title_summary, full_summary, and language
    """
    prompt = f"""You are an AI agent that processes trending posts from social media and news sources.
Never stop mid-output unless you reach a hard token limit.

Input:
- title: {topic.title}
- url: {topic.url}
- content: {topic.content if topic.content else topic.description if topic.description else "(no content available)"}
- language: {topic.language}

Tasks:
1. Generate a concise **title summary** using around 15 words, preserving the core meaning.
2. Summarize the post content in a **brief summary**, starting with the original link and original title.
   Example output start:
   "[{topic.url}] {topic.title}: ..."
3. Preserve the original language for content unless specified otherwise.
4. Ensure clarity, engagement, and factual correctness.
5. Output the results in JSON format exactly as follows:

{{
  "title_summary": "Concise 15-word summary of the original title",
  "full_summary": "[{topic.url}] {topic.title}: Brief summary of the post content",
  "language": "ISO language code of the output"
}}

Notes:
- If content is missing, generate the summary from the title and context alone.
- Keep the title summary close to 15 words, but only if it does not break clarity.
- Do not invent facts; summarize only the provided content or reliable context.
"""

    return await call_llm_json(prompt)


async def summarize(cluster, category_name=None):
    """
    Generate a summary for a cluster of related topics.

    Args:
        cluster: List of Topic objects
        category_name: Optional category name for context (e.g., "Technology", "Politics")

    Returns:
        Summary text from LLM
    """
    text = "\n".join([t.title for t in cluster])

    category_context = f"\nCategory: {category_name}" if category_name else ""

    prompt = f"""You are a professional trend analyst.

Summarize the following cluster into:
- Title: Use exactly "{category_name if category_name else 'General'}" as the first line (do not add "Trends" or any other words)
- 3 bullet key points
- 2 sentence explanation{category_context}

Text:
{text}

Note: These topics belong to the "{category_name}" category. The summary should reflect this context.
IMPORTANT: The title must be exactly "{category_name}" without adding "Trends" or any other suffix.
"""

    return await call_llm(prompt)
