from openai import OpenAI
import sys
import os
import json
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import OPENAI_API_KEY, MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def generate_mock_response(prompt):
    """
    Generate mock JSON response for testing without API calls.
    Extracts topics from prompt and creates mock summaries.
    """
    try:
        # Try to find JSON array in prompt - look for opening bracket to closing bracket
        start_idx = prompt.find('[')
        if start_idx == -1:
            # Not a batch request, return single result
            return {
                "title_summary": "Mock summary of the topic",
                "full_summary": "[URL] Title: Mock content summary here"
            }

        # Find the matching closing bracket
        bracket_count = 0
        end_idx = start_idx
        for i in range(start_idx, len(prompt)):
            if prompt[i] == '[':
                bracket_count += 1
            elif prompt[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break

        json_str = prompt[start_idx:end_idx]
        topics_json = json.loads(json_str)

        mock_results = []
        for topic_data in topics_json:
            title = topic_data.get('title', '')
            url = topic_data.get('url', '')
            content = topic_data.get('content', '')

            # Mock title_summary: first 15 words of title
            title_words = title.split()[:15]
            title_summary = ' '.join(title_words) if title_words else "Mock Title"

            # Mock full_summary: [URL] Title: first 100 words of content
            if content:
                content_words = content.split()[:100]
                full_summary = f"[{url}] {title}: {' '.join(content_words)}"
            else:
                # Use title if no content
                full_summary = f"[{url}] {title}"

            mock_results.append({
                "title_summary": title_summary,
                "full_summary": full_summary
            })

        return mock_results

    except Exception as e:
        print(f"Error generating mock response: {e}")
        # Return empty dict as fallback (better than empty list)
        return {
            "title_summary": "Mock summary (error fallback)",
            "full_summary": "[URL] Mock content summary (error fallback)"
        }


async def call_llm(prompt):
    """
    Call OpenAI API with a given prompt.

    Args:
        prompt: The prompt to send to the LLM

    Returns:
        LLM's response text
    """
    # ============================================================
    # REAL API CALL - Using OpenAI
    # ============================================================
    response = client.chat.completions.create(
        model=MODEL, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

    # ============================================================
    # MOCK MODE - FOR TESTING WITHOUT API CALLS (currently disabled)
    # ============================================================
    # print("\n" + "="*80)
    # print("=== MOCK MODE: Would send to OpenAI API ===")
    # print("="*80)
    # print(f"Model: {MODEL}")
    # print(f"Max Tokens: 1024")
    # print(f"Prompt Preview (first 500 chars):\n{prompt[:500]}...")
    # print("="*80)
    #
    # # MOCK RESPONSE (comment out when using real API)
    # mock_response = "Mock LLM response for testing"
    # print(f"=== MOCK MODE: Returning mock response ===\n{mock_response}\n" + "="*80 + "\n")
    # return mock_response


async def call_llm_json(prompt, max_tokens=1024):
    """
    Call OpenAI API with JSON mode enabled.

    Args:
        prompt: The prompt to send to the LLM (should request JSON output)
        max_tokens: Maximum tokens for response (default: 1024, use higher for batch)

    Returns:
        Parsed JSON object from LLM response
    """
    # ============================================================
    # REAL API CALL - Using OpenAI
    # ============================================================
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    content = response.choices[0].message.content
    return json.loads(content)

    # ============================================================
    # MOCK MODE - FOR TESTING WITHOUT API CALLS (currently disabled)
    # ============================================================
    # print("\n" + "="*80)
    # print("=== MOCK MODE: Would send to OpenAI API (JSON) ===")
    # print("="*80)
    # print(f"Model: {MODEL}")
    # print(f"Max Tokens: {max_tokens}")
    # print(f"Prompt Preview (first 800 chars):\n{prompt[:800]}...")
    # print("="*80)
    #
    # # MOCK RESPONSE (comment out when using real API)
    # mock_result = generate_mock_response(prompt)
    # print(f"=== MOCK MODE: Returning mock JSON ===")
    # print(f"Generated {len(mock_result) if isinstance(mock_result, list) else 1} mock summaries")
    # if isinstance(mock_result, list) and len(mock_result) > 0:
    #     print(f"Sample: {json.dumps(mock_result[0], indent=2)}")
    # print("="*80 + "\n")
    # return mock_result
