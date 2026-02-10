#!/usr/bin/env python3
"""
Compatibility wrapper for different Qdrant client versions.
Handles both old (1.7.x) and new (1.11.x+) API versions.
"""

from qdrant_client import QdrantClient
import warnings


def search_qdrant(client: QdrantClient, collection_name: str, query_vector, limit: int = 3):
    """
    Search in Qdrant collection with version compatibility.
    
    Works with all Qdrant client versions (1.7.x to 1.16.x+).
    """
    errors = []
    
    # Try 1: Newest API (1.16.0+) uses query_points with Query models
    if hasattr(client, 'query_points'):
        try:
            # Import Query model for v1.16+
            from qdrant_client.models import Query
            
            # Try with Query wrapper
            result = client.query_points(
                collection_name=collection_name,
                query=Query(query=query_vector),
                limit=limit
            )
            # query_points returns QueryResponse with .points attribute
            return result.points if hasattr(result, 'points') else result
        except Exception as e:
            errors.append(f"query_points with Query: {e}")
            
            # Try direct vector without Query wrapper
            try:
                result = client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=limit
                )
                return result.points if hasattr(result, 'points') else result
            except Exception as e2:
                errors.append(f"query_points direct: {e2}")
    
    # Try 2: Old API (1.7-1.15) uses .search()
    if hasattr(client, 'search'):
        try:
            return client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
        except Exception as e:
            errors.append(f"search with query_vector: {e}")
    
    # Try 3: Fallback for old search_batch
    if hasattr(client, 'search_batch'):
        try:
            from qdrant_client.models import SearchRequest
            search_requests = [
                SearchRequest(
                    vector=query_vector,
                    limit=limit
                )
            ]
            results = client.search_batch(
                collection_name=collection_name,
                requests=search_requests
            )
            return results[0] if results else []
        except Exception as e:
            errors.append(f"search_batch: {e}")
    
    # All attempts failed
    available_methods = [m for m in dir(client) if not m.startswith('_')]
    raise RuntimeError(
        f"All search attempts failed for Qdrant client.\n"
        f"Errors:\n" + "\n".join(f"  - {err}" for err in errors) +
        f"\n\nAvailable methods: {available_methods[:20]}"
    )


if __name__ == "__main__":
    # Test compatibility
    from qdrant_client import __version__ as qdrant_version
    print(f"Qdrant Client Version: {qdrant_version}")
    
    client = QdrantClient(":memory:")
    
    if hasattr(client, 'search'):
        print("✓ Has .search() method (new API)")
    else:
        print("✗ Missing .search() method")
    
    if hasattr(client, 'search_batch'):
        print("✓ Has .search_batch() method (old API)")
    else:
        print("✗ Missing .search_batch() method")
