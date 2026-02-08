from openai import OpenAI
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import OPENAI_API_KEY, EMBED_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def get_embeddings(texts):
    """
    Generate embeddings for a list of texts using OpenAI API.

    Args:
        texts: List of strings to embed

    Returns:
        NumPy array of embeddings with shape (len(texts), embedding_dim)
    """
    if not texts:
        return np.array([])

    # OpenAI embeddings API supports up to 2048 inputs per request
    # Current use case (50-120 topics) fits in one batch
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )

    # Convert to NumPy array for compatibility with scikit-learn
    embeddings = np.array([item.embedding for item in response.data])

    return embeddings
