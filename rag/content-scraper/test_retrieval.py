#!/usr/bin/env python3
"""
Test script for retrieval system.
Tests semantic search against the vector database.
"""

import sys
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import config


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
    print(f"Loading model: {config.EMBEDDING_MODEL}")
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    
    # Create query embedding
    print("Creating query embedding...")
    query_embedding = model.encode(query).tolist()
    
    # Connect to Qdrant
    print(f"Connecting to Qdrant ({config.QDRANT_HOST}:{config.QDRANT_PORT})...")
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    
    # Search
    print(f"Searching in collection: {config.COLLECTION_NAME}")
    try:
        search_result = client.search(
            collection_name=config.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print(f"  - Collection '{config.COLLECTION_NAME}' doesn't exist")
        print(f"  - Qdrant not running at {config.QDRANT_HOST}:{config.QDRANT_PORT}")
        print(f"  - No data ingested yet (run: python ingest_data.py)")
        return []
    
    # Format results
    results = []
    for hit in search_result:
        results.append({
            "text": hit.payload["text"],
            "score": hit.score,
            "source_url": hit.payload.get("source_url", "unknown"),
            "source_domain": hit.payload.get("source_domain", "unknown"),
            "chunk_index": hit.payload.get("chunk_index", 0),
            "content_hash": hit.payload.get("content_hash", "")[:8]  # First 8 chars
        })
    
    return results


def display_results(query: str, results: list):
    """Display search results in a formatted way."""
    print("\n" + "="*70)
    print(f"QUERY: {query}")
    print("="*70)
    
    if not results:
        print("\n❌ No results found.")
        print("\nTips:")
        print("  - Make sure you've run: python ingest_data.py")
        print("  - Try a different query")
        print("  - Check if Qdrant is running: docker ps | grep qdrant")
        return
    
    print(f"\nFound {len(results)} result(s):\n")
    
    for idx, result in enumerate(results, 1):
        score_bar = "█" * int(result['score'] * 20)
        print(f"{'─'*70}")
        print(f"Result {idx} │ Score: {result['score']:.4f} {score_bar}")
        print(f"{'─'*70}")
        print(f"Source: {result['source_domain']} (chunk #{result['chunk_index']})")
        print(f"URL: {result['source_url']}")
        print(f"Hash: {result['content_hash']}")
        print()
        print(result['text'])
        print()


def test_multiple_queries():
    """Run multiple test queries to evaluate the system."""
    test_queries = [
        "Wie lange dauert das Praxissemester?",
        "Wann findet das Praxissemester statt?",
        "Welche Module gibt es im Praxissemester?",
        "Kann ich das Praxissemester im Ausland machen?",
        "Wie bewerbe ich mich für das Praxissemester?",
    ]
    
    print("="*70)
    print("  TESTING RETRIEVAL SYSTEM")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Collection: {config.COLLECTION_NAME}")
    print(f"  Model: {config.EMBEDDING_MODEL}")
    print(f"  Top K: 2")
    print()
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print('='*70)
        
        results = retrieve_context(query, top_k=2)
        
        if results:
            for idx, result in enumerate(results, 1):
                print(f"\n--- Result {idx} (Score: {result['score']:.4f}) ---")
                print(f"Source: {result['source_domain']}")
                # Show first 200 chars
                text_preview = result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
                print(text_preview)
        else:
            print("No results found")
        
        print()


def main():
    """Command-line interface for retrieval."""
    if len(sys.argv) < 2:
        print("Usage: python test_retrieval.py <query> [top_k]")
        print("   or: python test_retrieval.py --test   (run test queries)")
        print()
        print("Examples:")
        print('  python test_retrieval.py "Wie lange dauert das Praxissemester?"')
        print('  python test_retrieval.py "Wann findet das PSS statt?" 5')
        print('  python test_retrieval.py --test')
        sys.exit(1)
    
    # Check for test mode
    if sys.argv[1] == "--test":
        test_multiple_queries()
        return
    
    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    print("="*70)
    print("  SEMANTIC SEARCH")
    print("="*70)
    print()
    
    results = retrieve_context(query, top_k)
    display_results(query, results)


if __name__ == "__main__":
    main()
