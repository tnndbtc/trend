from sklearn.cluster import AgglomerativeClustering
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from llm.embeddings import get_embeddings


def cluster(topics, k=12):
    """
    Cluster similar topics together using agglomerative clustering.

    Args:
        topics: List of Topic objects
        k: Number of clusters (default 12)

    Returns:
        List of clusters, where each cluster is a list of Topic objects
    """
    if not topics:
        return []

    if len(topics) < k:
        k = len(topics)

    texts = [t.title for t in topics]
    embeddings = get_embeddings(texts)

    model_cluster = AgglomerativeClustering(n_clusters=k)
    labels = model_cluster.fit_predict(embeddings)

    clusters = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(topics[idx])

    return list(clusters.values())
