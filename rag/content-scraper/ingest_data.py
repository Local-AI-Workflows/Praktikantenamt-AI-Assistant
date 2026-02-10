#!/usr/bin/env python3
"""
Content ingestion script with delta loading support.
Fetches content from multiple URLs, creates embeddings, and stores in Qdrant.
Includes duplicate detection and incremental updates.
"""

import requests
import hashlib
import uuid
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Set
from urllib.parse import urlparse
import config
from embeddings import EmbeddingModel, create_embeddings
from semantic_chunking import chunk_by_headings


def generate_content_hash(text: str) -> str:
    """Generate a unique hash for content to detect duplicates."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fetch_website_content(url: str) -> tuple[str, str, str]:
    """
    Fetch content from a website.
    Returns: (text_content, html_content, url)
    """
    print(f"  Fetching: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Store original HTML for semantic chunking
        html_content = response.content
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements only (keep nav for now, might have content)
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to find main content area first
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content', '.main-content']:
            main_content = soup.select_one(selector)
            if main_content:
                print(f"    ℹ Using main content selector: {selector}")
                soup = main_content
                break
        
        if not main_content:
            print(f"    ℹ No main content found, using full page (more inclusive)")
            # Still remove nav and footer for full page scraping
            for elem in soup(["nav", "footer"]):
                elem.decompose()
        
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up excessive whitespace while preserving sentence structure
        import re
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Replace multiple newlines with single newline
        text = re.sub(r'\n+', '\n', text)
        # Remove spaces before punctuation
        text = re.sub(r' +([.,;:!?])', r'\1', text)
        
        print(f"    ✓ Fetched {len(text)} characters")
        return text, html_content, url
        
    except Exception as e:
        print(f"    ✗ Error fetching {url}: {e}")
        return None, None, url


def extract_domain(url: str) -> str:
    """Extract domain name from URL for better identification."""
    parsed = urlparse(url)
    return parsed.netloc


def chunk_text(text: str, url: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, str]]:
    """
    Split text into overlapping chunks with metadata.
    Uses character-based sliding window for better context preservation.
    Each chunk includes content hash for duplicate detection.
    """
    chunks = []
    domain = extract_domain(url)
    
    # If text is shorter than chunk_size, return it as a single chunk
    if len(text) <= chunk_size:
        chunk_hash = generate_content_hash(text)
        chunks.append({
            "text": text,
            "source_url": url,
            "source_domain": domain,
            "chunk_index": 0,
            "content_hash": chunk_hash
        })
        return chunks
    
    # Use sliding window with overlap
    chunk_index = 0
    start = 0
    
    while start < len(text):
        # Define end of chunk
        end = start + chunk_size
        
        # If this is not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings (. ! ?) near the end position
            search_start = max(start + chunk_size - 100, start)
            search_end = min(end + 100, len(text))
            
            # Find the last sentence ending within search range
            best_break = None
            for i in range(search_end - 1, search_start - 1, -1):
                if text[i] in '.!?' and i + 1 < len(text) and text[i + 1] in ' \n':
                    best_break = i + 1
                    break
            
            if best_break:
                end = best_break
        else:
            end = len(text)
        
        # Extract chunk
        chunk_text = text[start:end].strip()
        
        # Only add non-empty chunks
        if chunk_text:
            chunk_hash = generate_content_hash(chunk_text)
            chunks.append({
                "text": chunk_text,
                "source_url": url,
                "source_domain": domain,
                "chunk_index": chunk_index,
                "content_hash": chunk_hash
            })
            chunk_index += 1
        
        # Move start position (with overlap)
        next_start = end - overlap
        
        # Avoid infinite loop - ensure we're always moving forward
        if next_start >= end:
            # Overlap is larger than chunk, just move to end
            start = end
        elif next_start <= start:
            # We're not moving forward, skip overlap
            start = end
        else:
            start = next_start
    
    return chunks


def get_existing_hashes(client: QdrantClient, collection_name: str) -> Set[str]:
    """
    Get all existing content hashes from the collection.
    Used for delta loading to detect duplicates.
    """
    try:
        # Check if collection exists
        collections = client.get_collections()
        if collection_name not in [c.name for c in collections.collections]:
            return set()
        
        # Scroll through all points and collect hashes
        existing_hashes = set()
        offset = None
        
        while True:
            result = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            points, next_offset = result
            
            for point in points:
                if point.payload and "content_hash" in point.payload:
                    existing_hashes.add(point.payload["content_hash"])
            
            if next_offset is None:
                break
            offset = next_offset
        
        return existing_hashes
        
    except Exception as e:
        print(f"  Warning: Could not fetch existing hashes: {e}")
        return set()




def store_in_qdrant(
    chunks: List[Dict[str, str]], 
    embeddings: List[List[float]], 
    client: QdrantClient,
    collection_name: str,
    existing_hashes: Set[str],
    force_recreate: bool = False
):
    """
    Store chunks and embeddings in Qdrant with duplicate detection.
    
    Args:
        chunks: List of chunk dictionaries
        embeddings: List of embedding vectors
        client: Qdrant client instance
        collection_name: Name of the collection
        existing_hashes: Set of existing content hashes
        force_recreate: If True, recreate collection from scratch
    """
    vector_size = len(embeddings[0])
    
    # Create or recreate collection
    if force_recreate:
        try:
            client.delete_collection(collection_name=collection_name)
            print(f"  Deleted existing collection: {collection_name}")
        except Exception:
            pass
    
    # Ensure collection exists
    collection_exists = False
    try:
        client.get_collection(collection_name=collection_name)
        print(f"  Using existing collection: {collection_name}")
        collection_exists = True
    except Exception:
        pass
    
    if not collection_exists:
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            print(f"  Created new collection: {collection_name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  Using existing collection: {collection_name}")
            else:
                print(f"  Warning: Collection operation failed, but continuing: {e}")
    
    # Filter out duplicates (delta loading)
    new_chunks = []
    new_embeddings = []
    duplicate_count = 0
    
    for chunk, embedding in zip(chunks, embeddings):
        if chunk["content_hash"] in existing_hashes:
            duplicate_count += 1
        else:
            new_chunks.append(chunk)
            new_embeddings.append(embedding)
    
    if duplicate_count > 0:
        print(f"  ℹ Skipped {duplicate_count} duplicate chunks (already in database)")
    
    if not new_chunks:
        print(f"  ℹ No new chunks to upload (all content already exists)")
        return
    
    # Prepare points for upload
    points = []
    for chunk, embedding in zip(new_chunks, new_embeddings):
        # Generate UUID from content hash for consistent, valid IDs
        # This ensures the same content always gets the same UUID
        point_id = str(uuid.UUID(chunk["content_hash"][:32]))
        
        # Build payload with optional heading field
        payload = {
            "text": chunk["text"],
            "source_url": chunk["source_url"],
            "source_domain": chunk["source_domain"],
            "chunk_index": chunk["chunk_index"],
            "content_hash": chunk["content_hash"]
        }
        
        # Add heading if present (from semantic chunking)
        if "heading" in chunk and chunk["heading"]:
            payload["heading"] = chunk["heading"]
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload
        )
        points.append(point)
    
    # Upload to Qdrant
    print(f"  Uploading {len(points)} new chunks to Qdrant...")
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    print(f"  ✓ Upload complete!")


def main(force_recreate: bool = False):
    """
    Main ingestion pipeline.
    
    Args:
        force_recreate: If True, delete and recreate the collection (no delta loading)
    """
    print("="*70)
    print("  CONTENT INGESTION PIPELINE")
    print("="*70)
    print()
    
    # Display configuration
    print(f"Configuration:")
    print(f"  Collection: {config.COLLECTION_NAME}")
    print(f"  Qdrant: {config.QDRANT_HOST}:{config.QDRANT_PORT}")
    print(f"  Embedding Backend: {config.EMBEDDING_BACKEND}")
    if config.EMBEDDING_BACKEND == "sentence-transformers":
        print(f"  Model: {config.EMBEDDING_MODEL}")
    elif config.EMBEDDING_BACKEND == "ollama":
        print(f"  Ollama Host: {config.OLLAMA_HOST}")
        print(f"  Ollama Model: {config.OLLAMA_MODEL}")
    print(f"  Chunk size: {config.CHUNK_SIZE} chars (overlap: {config.CHUNK_OVERLAP})")
    print(f"  Source URLs: {len(config.SOURCE_URLS)}")
    print(f"  Mode: {'FULL REFRESH' if force_recreate else 'DELTA LOADING'}")
    print()
    
    # Connect to Qdrant early to get existing hashes
    print("Connecting to Qdrant...")
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    print("  ✓ Connected")
    print()
    
    # Get existing content hashes for delta loading
    existing_hashes = set()
    if not force_recreate:
        print("Checking for existing content (delta loading)...")
        existing_hashes = get_existing_hashes(client, config.COLLECTION_NAME)
        print(f"  Found {len(existing_hashes)} existing chunks in database")
        print()
    
    # 1. Fetch content from all URLs
    print(f"Fetching content from {len(config.SOURCE_URLS)} URL(s)...")
    all_content = []
    for url in config.SOURCE_URLS:
        text_content, html_content, source_url = fetch_website_content(url)
        if text_content:
            all_content.append((text_content, html_content, source_url))
    print(f"  ✓ Successfully fetched {len(all_content)} source(s)")
    print()
    
    if not all_content:
        print("  ✗ No content fetched. Exiting.")
        return
    
    # 2. Chunk all content using semantic chunking (by headings)
    print("Chunking content (semantic chunking by headings)...")
    all_chunks = []
    for text_content, html_content, url in all_content:
        # Use semantic chunking (by HTML structure)
        chunks = chunk_by_headings(html_content, url, max_chunk_size=config.CHUNK_SIZE * 2)
        all_chunks.extend(chunks)
        print(f"  Created {len(chunks)} semantic chunks from {url}")
    print(f"  ✓ Total chunks: {len(all_chunks)}")
    print()
    
    # 3. Load embedding model
    print(f"Loading embedding model...")
    model = EmbeddingModel()
    print()
    
    # 4. Create embeddings
    texts = [chunk["text"] for chunk in all_chunks]
    embeddings = create_embeddings(texts, model)
    print(f"  ✓ Created {len(embeddings)} embeddings (dimension: {len(embeddings[0])})")
    print()
    
    # 5. Store in Qdrant
    print("Storing in Qdrant...")
    store_in_qdrant(
        all_chunks, 
        embeddings, 
        client, 
        config.COLLECTION_NAME,
        existing_hashes,
        force_recreate
    )
    
    # Get final statistics
    print()
    print("="*70)
    print("  INGESTION COMPLETE")
    print("="*70)
    print(f"Collection: {config.COLLECTION_NAME}")
    
    try:
        collection_info = client.get_collection(collection_name=config.COLLECTION_NAME)
        print(f"Total vectors in database: {collection_info.points_count}")
        print(f"Vector dimension: {collection_info.config.params.vectors.size}")
        print(f"Distance metric: {collection_info.config.params.vectors.distance}")
    except Exception as e:
        print(f"Note: Could not retrieve collection statistics (client/server version mismatch)")
        print(f"  Ingestion completed successfully, but statistics unavailable")
        print(f"  Consider upgrading qdrant-client: pip install --upgrade qdrant-client")
    
    print("="*70)


if __name__ == "__main__":
    import sys
    
    # Check for --force flag to recreate collection
    force_recreate = "--force" in sys.argv or "--recreate" in sys.argv
    
    if force_recreate:
        print("\n⚠️  FORCE MODE: Will delete and recreate collection\n")
    
    main(force_recreate=force_recreate)
