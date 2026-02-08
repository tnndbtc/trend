from sklearn.metrics.pairwise import cosine_similarity
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from llm.embeddings import get_embeddings


def deduplicate(topics, threshold=0.92):
    """
    Remove duplicate topics using embedding similarity.

    Args:
        topics: List of Topic objects
        threshold: Cosine similarity threshold (default 0.92)

    Returns:
        List of unique topics
    """
    if not topics:
        return []

    texts = [t.title for t in topics]
    embeddings = get_embeddings(texts)
    sim = cosine_similarity(embeddings)

    used = set()
    unique = []

    for i in range(len(topics)):
        if i in used:
            continue
        used.add(i)
        for j in range(i + 1, len(topics)):
            if sim[i][j] > threshold:
                used.add(j)
        unique.append(topics[i])

    return unique
