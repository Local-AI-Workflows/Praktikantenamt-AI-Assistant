"""
Configuration module for the content scraping and retrieval system.
Loads settings from environment variables with sensible defaults.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "htwg_knowledge_base")

# Embedding Model Configuration
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", 
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Chunking Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Data Source URLs
def get_source_urls() -> List[str]:
    """
    Get list of URLs to scrape from environment variable.
    Returns a list of URLs, split by comma.
    """
    urls_str = os.getenv("SOURCE_URLS", "")
    if not urls_str:
        # Default URL if none specified
        return ["https://www.htwg-konstanz.de/hochschule/fakultaeten/informatik/studium/praxissemester-bachelor"]
    
    # Split by comma and strip whitespace
    urls = [url.strip() for url in urls_str.split(",") if url.strip()]
    return urls

SOURCE_URLS = get_source_urls()

# Display configuration on import
if __name__ == "__main__":
    print("=== Configuration ===")
    print(f"Qdrant Host: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Embedding Model: {EMBEDDING_MODEL}")
    print(f"Chunk Size: {CHUNK_SIZE} chars (overlap: {CHUNK_OVERLAP})")
    print(f"Source URLs ({len(SOURCE_URLS)}):")
    for idx, url in enumerate(SOURCE_URLS, 1):
        print(f"  {idx}. {url}")
