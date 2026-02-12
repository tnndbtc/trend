from django import template
import re

register = template.Library()


@register.filter
def remove_url_prefix(text):
    """
    Remove [URL] prefix from summary text.
    Example: "[https://example.com] Title: content" -> "Title: content"
    """
    if not text:
        return text

    # Remove [URL] pattern at the start of the text
    pattern = r'^\[https?://[^\]]+\]\s*'
    cleaned_text = re.sub(pattern, '', text)

    return cleaned_text
