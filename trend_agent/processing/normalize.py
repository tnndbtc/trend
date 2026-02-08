def normalize(topics):
    """Normalize topic text by stripping whitespace."""
    for t in topics:
        t.title = t.title.strip()
        t.description = t.description.strip()
    return topics
