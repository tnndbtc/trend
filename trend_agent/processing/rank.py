def score_cluster(cluster):
    """
    Calculate engagement score for a cluster based on metrics.

    Args:
        cluster: List of Topic objects

    Returns:
        Total engagement score
    """
    score = 0
    for t in cluster:
        score += t.metrics.get("upvotes", 0)
        score += t.metrics.get("comments", 0)
        score += t.metrics.get("score", 0)
    return score


def rank_clusters(clusters):
    """
    Rank clusters by their engagement scores in descending order.

    Args:
        clusters: List of clusters

    Returns:
        Sorted list of clusters (highest score first)
    """
    return sorted(clusters, key=score_cluster, reverse=True)
