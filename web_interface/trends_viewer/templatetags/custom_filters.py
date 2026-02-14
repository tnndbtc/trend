from django import template
import re
from ..translations import translate_category

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


@register.filter
def translate_cat(category_name, lang_code='en-US'):
    """
    Translate a category name to the specified language.

    Usage in template:
        {{ trend.category|translate_cat:current_lang }}

    Args:
        category_name: English category name (e.g., 'Technology')
        lang_code: Target language code (e.g., 'zh-Hans')

    Returns:
        Translated category name
    """
    if not category_name:
        return category_name

    return translate_category(category_name, lang_code or 'en-US')
