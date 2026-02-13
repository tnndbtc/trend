"""Custom template filters for source formatting."""

from django import template

register = template.Library()


@register.filter
def format_source_class(value):
    """
    Format source value for use in CSS class names.

    Examples:
        SourceType.CUSTOM -> custom
        SourceType.BBC -> bbc
        reddit -> reddit
        google_news -> google_news
    """
    if not value:
        return value

    # Convert to string in case it's an enum
    value_str = str(value)

    # Handle SourceType enum values (e.g., "SourceType.CUSTOM" -> "custom")
    if value_str.startswith('SourceType.'):
        value_str = value_str.replace('SourceType.', '').lower()

    # Return lowercase value for CSS class
    return value_str.lower()


@register.filter
def format_source_name(topic_or_value):
    """
    Format source name for display.

    If passed a topic object with source_name, uses that.
    Otherwise formats the source field.

    Examples:
        topic with source_name='Wenxuecity News' -> Wenxuecity News
        'reddit' -> Reddit
        'hackernews' -> Hacker News
        'google_news' -> Google News
        'SourceType.CUSTOM' -> Custom
        'SourceType.BBC' -> BBC
    """
    # If it's a topic object with source_name, use that
    if hasattr(topic_or_value, 'source_name') and topic_or_value.source_name:
        return topic_or_value.source_name

    # If it's a topic object, get the source field
    if hasattr(topic_or_value, 'source'):
        value = topic_or_value.source
    else:
        value = topic_or_value

    if not value:
        return value

    # Convert to string in case it's an enum
    value_str = str(value)

    # Handle SourceType enum values (e.g., "SourceType.CUSTOM" -> "custom")
    if value_str.startswith('SourceType.'):
        value_str = value_str.replace('SourceType.', '').lower()

    # Convert to lowercase for comparison
    value_lower = value_str.lower()

    # Special case mappings
    special_cases = {
        'google_news': 'Google News',
        'ap_news': 'AP News',
        'al_jazeera': 'Al Jazeera',
        'hackernews': 'Hacker News',
        'bbc': 'BBC',
        'guardian': 'The Guardian',
        'reuters': 'Reuters',
        'custom': 'Custom',
        'demo': 'Demo',
    }

    # Check if it's a special case
    if value_lower in special_cases:
        return special_cases[value_lower]

    # Default: replace underscores with spaces and title case
    return value_lower.replace('_', ' ').title()
