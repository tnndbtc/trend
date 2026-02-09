from sklearn.metrics.pairwise import cosine_similarity
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from llm.embeddings import get_embeddings


def deduplicate(topics, threshold=0.92, debug=False):
    """
    Remove duplicate topics using embedding similarity.

    Args:
        topics: List of Topic objects
        threshold: Cosine similarity threshold (default 0.92)
        debug: Print similarity scores for debugging (default False)

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
    duplicates_found = []
    all_comparisons = []

    for i in range(len(topics)):
        if i in used:
            continue
        used.add(i)
        for j in range(i + 1, len(topics)):
            if debug:
                all_comparisons.append((i, j, sim[i][j], topics[i].title[:60], topics[j].title[:60]))
            if sim[i][j] > threshold:
                used.add(j)
                duplicates_found.append((i, j, sim[i][j], topics[i].title[:60], topics[j].title[:60]))
        unique.append(topics[i])

    if debug:
        print(f"\n=== Deduplication Debug (threshold={threshold}) ===")
        print(f"Total topics: {len(topics)}, Unique after dedup: {len(unique)}")

        if duplicates_found:
            print(f"\nRemoved {len(duplicates_found)} duplicate(s):")
            for i, j, similarity, title1, title2 in duplicates_found:
                print(f"  Similarity={similarity:.3f} (>{threshold}):")
                print(f"    Kept:    [{i}] {title1}...")
                print(f"    Removed: [{j}] {title2}...")

        # Show high similarity pairs that weren't caught
        high_sim_not_removed = [(i, j, s, t1, t2) for i, j, s, t1, t2 in all_comparisons
                                if s > 0.70 and s <= threshold and j not in used]
        if high_sim_not_removed:
            print(f"\nHigh similarity pairs below threshold (not removed):")
            for i, j, similarity, title1, title2 in high_sim_not_removed[:5]:  # Show top 5
                print(f"  Similarity={similarity:.3f} (<={threshold}):")
                print(f"    [{i}] {title1}...")
                print(f"    [{j}] {title2}...")

    return unique
