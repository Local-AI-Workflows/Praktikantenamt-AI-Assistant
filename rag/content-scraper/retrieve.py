#!/usr/bin/env python3
"""
Retrieval script for querying the vector database.
Can be used standalone or called from n8n.
"""

import sys
from qdrant_client import QdrantClient
import config
from embeddings import EmbeddingModel


def retrieve_context(query: str, top_k: int = 3) -> list:
    """
    Retrieve relevant context from the vector database.
    
    Args:
        query: The search query
        top_k: Number of results to return
    
    Returns:
        List of dictionaries with text and metadata
    """
    # Load model
    model = EmbeddingModel()
    
    # Create query embedding
    query_embedding = model.encode(query).tolist()
    
    # Connect to Qdrant
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    
    # Search
    search_result = client.search(
        collection_name=config.COLLECTION_NAME,
        query_vector=query_embedding,
        limit=top_k
    )
    
    # Format results
    results = []
    for hit in search_result:
        results.append({
            "text": hit.payload["text"],
            "score": hit.score,
            "source": hit.payload["source"],
            "chunk_id": hit.payload["chunk_id"]
        })
    
    return results


def main():
    """Command-line interface for retrieval."""
    if len(sys.argv) < 2:
        print("Usage: python retrieve.py <query> [top_k]")
        sys.exit(1)
    
    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    print(f"Query: {query}")
    print(f"Retrieving top {top_k} results...\n")
    
    results = retrieve_context(query, top_k)
    
    print(f"Found {len(results)} results:\n")
    for idx, result in enumerate(results, 1):
        print(f"--- Result {idx} (Score: {result['score']:.4f}) ---")
        print(result['text'])
        print(f"Source: {result['source']}")
        print()


if __name__ == "__main__":
    main()
