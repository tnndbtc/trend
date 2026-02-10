"""Custom template filters for source formatting."""

from django import template

register = template.Library()


@register.filter
def format_source_name(value):
    """
    Format source name for display.

    Examples:
        reddit -> Reddit
        hackernews -> Hackernews
        google_news -> Google News
        ap_news -> AP News
        al_jazeera -> Al Jazeera
    """
    if not value:
        return value

    # Special case mappings
    special_cases = {
        'google_news': 'Google News',
        'ap_news': 'AP News',
        'al_jazeera': 'Al Jazeera',
        'hackernews': 'Hacker News',
        'bbc': 'BBC',
        'guardian': 'The Guardian',
        'reuters': 'Reuters',
    }

    # Check if it's a special case
    if value in special_cases:
        return special_cases[value]

    # Default: replace underscores with spaces and title case
    return value.replace('_', ' ').title()
