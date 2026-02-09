from sklearn.cluster import AgglomerativeClustering
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from llm.embeddings import get_embeddings
from categories import load_categories


def cluster(topics, categories=None):
    """
    Cluster similar topics together by broad categories using agglomerative clustering.

    Groups topics into predefined broad categories like Entertainment, Politics,
    Technology, Sports, Science, etc.

    Args:
        topics: List of Topic objects
        categories: List of category names to use (default: load from categories.json)

    Returns:
        tuple: (clusters, category_names) where:
            - clusters: List of clusters, where each cluster is a list of Topic objects
            - category_names: List of category names corresponding to each cluster
    """
    # Load categories if not provided
    if categories is None:
        categories = load_categories()

    k = len(categories)

    if not topics:
        return [], categories

    # Special case: single topic
    if len(topics) == 1:
        return [topics], [categories[0]]

    # If fewer topics than desired clusters, reduce k and trim categories
    if len(topics) < k:
        k = len(topics)
        categories = categories[:k]

    # Generate embeddings from topic titles
    texts = [t.title for t in topics]
    embeddings = get_embeddings(texts)

    # Use fixed k clustering to force broad category grouping
    model_cluster = AgglomerativeClustering(
        n_clusters=k,
        metric='cosine',              # Use cosine similarity
        linkage='average'             # Average linkage for better grouping
    )

    labels = model_cluster.fit_predict(embeddings)

    # Group topics by cluster label
    clusters = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(topics[idx])

    # Return clusters in order with corresponding category names
    ordered_clusters = []
    used_categories = []
    for label in sorted(clusters.keys()):
        ordered_clusters.append(clusters[label])
        # Assign category names in order
        if label < len(categories):
            used_categories.append(categories[label])
        else:
            used_categories.append(f"Category {label + 1}")

    return ordered_clusters, used_categories
