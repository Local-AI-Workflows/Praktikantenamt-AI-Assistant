#!/usr/bin/env python3
"""
Content ingestion script with delta loading support.
Fetches content from multiple URLs, creates embeddings, and stores in Qdrant.
Includes duplicate detection and incremental updates.
"""

import requests
import hashlib
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from typing import List, Dict, Set
from urllib.parse import urlparse
import config


def generate_content_hash(text: str) -> str:
    """Generate a unique hash for content to detect duplicates."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fetch_website_content(url: str) -> tuple[str, str]:
    """
    Fetch content from a website.
    Returns: (text_content, url)
    """
    print(f"  Fetching: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        print(f"    ✓ Fetched {len(text)} characters")
        return text, url
        
    except Exception as e:
        print(f"    ✗ Error fetching {url}: {e}")
        return None, url


def extract_domain(url: str) -> str:
    """Extract domain name from URL for better identification."""
    parsed = urlparse(url)
    return parsed.netloc


def chunk_text(text: str, url: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, str]]:
    """
    Split text into overlapping chunks with metadata.
    Each chunk includes content hash for duplicate detection.
    """
    chunks = []
    sentences = text.split('. ')
    current_chunk = ""
    chunk_index = 0
    domain = extract_domain(url)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunk_text = current_chunk.strip()
                chunk_hash = generate_content_hash(chunk_text)
                
                chunks.append({
                    "text": chunk_text,
                    "source_url": url,
                    "source_domain": domain,
                    "chunk_index": chunk_index,
                    "content_hash": chunk_hash
                })
                chunk_index += 1
            current_chunk = sentence + ". "
    
    # Add the last chunk
    if current_chunk:
        chunk_text = current_chunk.strip()
        chunk_hash = generate_content_hash(chunk_text)
        chunks.append({
            "text": chunk_text,
            "source_url": url,
            "source_domain": domain,
            "chunk_index": chunk_index,
            "content_hash": chunk_hash
        })
    
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


def create_embeddings(texts: List[str], model: SentenceTransformer) -> List[List[float]]:
    """Create embeddings for text chunks."""
    print(f"  Creating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings.tolist()


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
    try:
        client.get_collection(collection_name=collection_name)
        print(f"  Using existing collection: {collection_name}")
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print(f"  Created new collection: {collection_name}")
    
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
        # Use content hash as ID to ensure true uniqueness
        point_id = chunk["content_hash"][:32]  # Use first 32 chars of hash as ID
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "text": chunk["text"],
                "source_url": chunk["source_url"],
                "source_domain": chunk["source_domain"],
                "chunk_index": chunk["chunk_index"],
                "content_hash": chunk["content_hash"]
            }
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
    print(f"  Model: {config.EMBEDDING_MODEL}")
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
        content, source_url = fetch_website_content(url)
        if content:
            all_content.append((content, source_url))
    print(f"  ✓ Successfully fetched {len(all_content)} source(s)")
    print()
    
    if not all_content:
        print("  ✗ No content fetched. Exiting.")
        return
    
    # 2. Chunk all content
    print("Chunking content...")
    all_chunks = []
    for content, url in all_content:
        chunks = chunk_text(
            content, 
            url, 
            chunk_size=config.CHUNK_SIZE, 
            overlap=config.CHUNK_OVERLAP
        )
        all_chunks.extend(chunks)
        print(f"  Created {len(chunks)} chunks from {url}")
    print(f"  ✓ Total chunks: {len(all_chunks)}")
    print()
    
    # 3. Load embedding model
    print(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    print("  ✓ Model loaded")
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
    collection_info = client.get_collection(collection_name=config.COLLECTION_NAME)
    
    print()
    print("="*70)
    print("  INGESTION COMPLETE")
    print("="*70)
    print(f"Collection: {config.COLLECTION_NAME}")
    print(f"Total vectors in database: {collection_info.points_count}")
    print(f"Vector dimension: {collection_info.config.params.vectors.size}")
    print(f"Distance metric: {collection_info.config.params.vectors.distance}")
    print("="*70)


if __name__ == "__main__":
    import sys
    
    # Check for --force flag to recreate collection
    force_recreate = "--force" in sys.argv or "--recreate" in sys.argv
    
    if force_recreate:
        print("\n⚠️  FORCE MODE: Will delete and recreate collection\n")
    
    main(force_recreate=force_recreate)
