def normalize(topics):
    """Normalize topic text by stripping whitespace and handling None values."""
    for t in topics:
        # Always normalize title (required field)
        if t.title:
            t.title = t.title.strip()

        # Normalize description only if it exists (optional field)
        if t.description:
            t.description = t.description.strip()

    return topics
