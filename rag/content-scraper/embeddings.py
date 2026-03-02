#!/usr/bin/env python3
"""
Embedding module that supports multiple backends.
Provides a unified interface for creating embeddings using either
Sentence Transformers or Ollama.
"""

from typing import List, Union
import numpy as np
import config


class EmbeddingModel:
    """Unified interface for embedding models."""
    
    def __init__(self):
        """Initialize the embedding model based on configuration."""
        self.backend = config.EMBEDDING_BACKEND
        self.model = None
        
        if self.backend == "sentence-transformers":
            self._init_sentence_transformers()
        elif self.backend == "ollama":
            self._init_ollama()
        else:
            raise ValueError(f"Unknown embedding backend: {self.backend}")
    
    def _init_sentence_transformers(self):
        """Initialize Sentence Transformers model."""
        from sentence_transformers import SentenceTransformer
        print(f"  Loading Sentence Transformers model: {config.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        print(f"  ✓ Model loaded")
    
    def _init_ollama(self):
        """Initialize Ollama client."""
        import requests
        print(f"  Connecting to Ollama at {config.OLLAMA_HOST}")
        print(f"  Using model: {config.OLLAMA_MODEL}")
        
        # Test connection
        try:
            response = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5)
            response.raise_for_status()
            print(f"  ✓ Connected to Ollama")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Ollama at {config.OLLAMA_HOST}: {e}")
    
    def encode(self, texts: Union[str, List[str]], show_progress_bar: bool = False) -> np.ndarray:
        """
        Encode text(s) into embeddings.
        
        Args:
            texts: Single text string or list of text strings
            show_progress_bar: Whether to show progress bar (only for Sentence Transformers)
        
        Returns:
            numpy array of embeddings
        """
        # Convert single string to list
        if isinstance(texts, str):
            texts = [texts]
            single_input = True
        else:
            single_input = False
        
        # Get embeddings based on backend
        if self.backend == "sentence-transformers":
            embeddings = self._encode_sentence_transformers(texts, show_progress_bar)
        elif self.backend == "ollama":
            embeddings = self._encode_ollama(texts, show_progress_bar)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
        
        # Return single embedding if input was a single string
        if single_input:
            return embeddings[0]
        return embeddings
    
    def _encode_sentence_transformers(self, texts: List[str], show_progress_bar: bool) -> np.ndarray:
        """Encode texts using Sentence Transformers."""
        return self.model.encode(texts, show_progress_bar=show_progress_bar)
    
    def _encode_ollama(self, texts: List[str], show_progress_bar: bool) -> np.ndarray:
        """Encode texts using Ollama."""
        import requests
        from tqdm import tqdm
        
        embeddings = []
        iterator = tqdm(texts, desc="Creating embeddings") if show_progress_bar else texts
        
        for text in iterator:
            try:
                response = requests.post(
                    f"{config.OLLAMA_HOST}/api/embeddings",
                    json={
                        "model": config.OLLAMA_MODEL,
                        "prompt": text
                    },
                    timeout=30
                )
                response.raise_for_status()
                embedding = response.json()["embedding"]
                embeddings.append(embedding)
            except Exception as e:
                raise RuntimeError(f"Failed to get embedding from Ollama: {e}")
        
        return np.array(embeddings)
    
    def get_dimension(self) -> int:
        """
        Get the dimension of the embeddings.
        
        Returns:
            Integer dimension of embeddings
        """
        # Create a test embedding to get dimension
        test_embedding = self.encode("test")
        return len(test_embedding)


def create_embeddings(texts: List[str], model: EmbeddingModel) -> List[List[float]]:
    """
    Create embeddings for text chunks.
    
    Args:
        texts: List of text strings to embed
        model: EmbeddingModel instance
    
    Returns:
        List of embedding vectors
    """
    print(f"  Creating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings.tolist()


if __name__ == "__main__":
    # Test the embedding model
    print("=== Testing Embedding Model ===")
    print(f"Backend: {config.EMBEDDING_BACKEND}")
    
    model = EmbeddingModel()
    
    # Test single text
    test_text = "Dies ist ein Test."
    embedding = model.encode(test_text)
    print(f"\nTest text: {test_text}")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
    
    # Test multiple texts
    test_texts = [
        "Hallo Welt",
        "Wie geht es dir?",
        "Das Wetter ist schön."
    ]
    embeddings = model.encode(test_texts)
    print(f"\nTest texts: {len(test_texts)}")
    print(f"Embeddings shape: {embeddings.shape}")
