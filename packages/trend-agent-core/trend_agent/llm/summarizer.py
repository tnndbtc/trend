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
            "url": str(t.url),  # Convert HttpUrl to string for JSON serialization
            "content": content,
            "language": t.language
        })

    prompt = f"""You are an AI agent that processes trending posts from social media and news sources.
Process these {len(topics)} topics and return a JSON array with summaries.

**CRITICAL: ALL OUTPUT MUST BE IN ENGLISH regardless of input language.**
If input is in Chinese, Japanese, Korean, or any non-English language, translate to English while preserving meaning and nuance.

Input topics:
{json.dumps(topics_data, indent=2)}

For EACH topic, generate:
1. title_summary: A concise ENGLISH summary using around 15 words, preserving the core meaning
2. full_summary: MUST start with "[URL] Original Title: " then provide a FULL-LENGTH ENGLISH REWRITE of the content

CRITICAL REQUIREMENTS for full_summary:
- START with "[{{url}}] {{original_title}}: " format (translate title to English if needed)
- Then provide a comprehensive ENGLISH rewrite that is approximately THE SAME LENGTH as the original content
- This is NOT a brief summary - rewrite the entire content in a clear, engaging way
- Preserve all key points, details, examples, and nuances from the original
- Target: ~100% of original content length (full rewrite, not condensed)
- **TRANSLATE non-English content to English**

Example:
{{
  "title_summary": "New AI model achieves breakthrough in reasoning tasks",
  "full_summary": "[https://example.com/post] Original Post Title: Researchers at XYZ Lab announce a groundbreaking new AI model... [continues with full-length rewrite of entire content]",
  "language": "en"
}}

Output MUST be a JSON array with exactly {len(topics)} objects:
[
  {{
    "title_summary": "...",
    "full_summary": "[URL] Title: [Full-length rewrite here...]",
    "language": "en"
  }},
  ...
]

Important:
- Generate full-length rewrites for ALL {len(topics)} topics
- **TRANSLATE all content to ENGLISH** (this is critical for ranking and clustering)
- Keep title_summary around 15 words
- ALWAYS include the [URL] and original title prefix in full_summary
- Full_summary should be approximately the same length as the original content
- Do not invent facts; rewrite only the provided content
- If original content is short, the rewrite can be proportionally short
- Set language field to "en" for all outputs
"""

    try:
        # Use much higher token limit for full-length rewrites (approx 1500-2000 tokens per topic)
        # Adjust based on batch size to avoid hitting API limits
        max_tokens = min(8000, len(topics) * 1800)
        result = await call_llm_json(prompt, max_tokens=max_tokens)

        # Ensure result is an array
        if isinstance(result, dict) and 'summaries' in result:
            return result['summaries']
        elif isinstance(result, list):
            return result
        else:
            # Fallback: return empty summaries
            return [{"title_summary": t.title, "full_summary": f"[{str(t.url)}] {t.title}"} for t in topics]

    except Exception as e:
        print(f"Batch summarization error: {e}")
        # Fallback: return basic summaries
        return [{"title_summary": t.title, "full_summary": f"[{str(t.url)}] {t.title}"} for t in topics]


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

**CRITICAL: ALL OUTPUT MUST BE IN ENGLISH regardless of input language.**
If input is in Chinese, Japanese, Korean, or any non-English language, translate to English while preserving meaning and nuance.

Input:
- title: {topic.title}
- url: {topic.url}
- content: {topic.content if topic.content else topic.description if topic.description else "(no content available)"}
- original_language: {topic.language}

Tasks:
1. Generate a concise **ENGLISH title summary** using around 15 words, preserving the core meaning.
2. Generate a **full-length ENGLISH rewrite** of the post content, starting with the original link and translated title.
   - START with: "[{topic.url}] {topic.title}: " (translate title to English if needed)
   - Then provide a comprehensive ENGLISH rewrite that is approximately THE SAME LENGTH as the original content
   - This is NOT a brief summary - rewrite the entire content in a clear, engaging way
   - Preserve all key points, details, examples, and nuances from the original
   - Target: ~100% of original content length (full rewrite, not condensed)
   - **TRANSLATE non-English content to English**
3. Ensure clarity, engagement, and factual correctness.
4. Output the results in JSON format exactly as follows:

{{
  "title_summary": "Concise 15-word ENGLISH summary of the original title",
  "full_summary": "[{topic.url}] Translated Title: Full-length ENGLISH rewrite of the entire post content...",
  "language": "en"
}}

Notes:
- If content is missing, generate from the title and context alone (proportionally shorter).
- Keep the title summary close to 15 words, but only if it does not break clarity.
- Full_summary should match the length of the original content (not abbreviated).
- Do not invent facts; rewrite only the provided content or reliable context.
- **Always output in English** - this is critical for ranking and clustering.
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
