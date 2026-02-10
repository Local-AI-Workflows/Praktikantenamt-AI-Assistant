#!/usr/bin/env python3
"""
Semantic chunking based on HTML structure (headings).
Creates chunks that respect document structure instead of arbitrary character limits.
"""

from bs4 import BeautifulSoup, NavigableString
from typing import List, Dict
import hashlib


def generate_content_hash(text: str) -> str:
    """Generate a unique hash for content."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def chunk_by_headings(html_content: str, url: str, max_chunk_size: int = 2000) -> List[Dict[str, str]]:
    """
    Chunk HTML content by headings, keeping semantic sections together.
    
    Args:
        html_content: Raw HTML content
        url: Source URL
        max_chunk_size: Maximum size for a chunk (will try to split large sections)
    
    Returns:
        List of chunk dictionaries
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer']):
        element.decompose()
    
    # Try to find main content
    main_content = None
    for selector in ['main', 'article', '[role="main"]', '.content', '#content']:
        main_content = soup.select_one(selector)
        if main_content:
            soup = main_content
            break
    
    chunks = []
    chunk_index = 0
    
    # Find all headings (h1-h6)
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    if not headings:
        # No headings found, fall back to paragraph-based chunking
        return _chunk_by_paragraphs(soup, url, max_chunk_size)
    
    # Process each section defined by headings
    for i, heading in enumerate(headings):
        # Get the heading text
        heading_text = heading.get_text(strip=True)
        
        # Get all content until the next heading
        section_elements = []
        current = heading.next_sibling
        
        # Collect all elements until next heading
        while current:
            # Stop if we hit the next heading
            if hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            
            # Add text content
            if isinstance(current, NavigableString):
                text = str(current).strip()
                if text:
                    section_elements.append(text)
            elif hasattr(current, 'get_text'):
                text = current.get_text(separator=' ', strip=True)
                if text:
                    section_elements.append(text)
            
            current = current.next_sibling
        
        # Combine heading with section content
        section_text = heading_text
        if section_elements:
            section_text += ': ' + ' '.join(section_elements)
        
        section_text = section_text.strip()
        
        # If section is too large, split it
        if len(section_text) > max_chunk_size:
            sub_chunks = _split_large_section(section_text, heading_text, max_chunk_size)
            for sub_chunk in sub_chunks:
                chunk_hash = generate_content_hash(sub_chunk)
                chunks.append({
                    'text': sub_chunk,
                    'source_url': url,
                    'source_domain': _extract_domain(url),
                    'chunk_index': chunk_index,
                    'content_hash': chunk_hash,
                    'heading': heading_text
                })
                chunk_index += 1
        else:
            # Add as single chunk
            if section_text:
                chunk_hash = generate_content_hash(section_text)
                chunks.append({
                    'text': section_text,
                    'source_url': url,
                    'source_domain': _extract_domain(url),
                    'chunk_index': chunk_index,
                    'content_hash': chunk_hash,
                    'heading': heading_text
                })
                chunk_index += 1
    
    return chunks


def _chunk_by_paragraphs(soup: BeautifulSoup, url: str, max_chunk_size: int) -> List[Dict[str, str]]:
    """Fallback: chunk by paragraphs if no headings found."""
    chunks = []
    chunk_index = 0
    
    # Get all paragraphs
    paragraphs = soup.find_all('p')
    
    current_chunk = ""
    
    for para in paragraphs:
        para_text = para.get_text(strip=True)
        
        if not para_text:
            continue
        
        # If adding this paragraph exceeds max size, save current chunk
        if current_chunk and len(current_chunk) + len(para_text) > max_chunk_size:
            chunk_hash = generate_content_hash(current_chunk)
            chunks.append({
                'text': current_chunk.strip(),
                'source_url': url,
                'source_domain': _extract_domain(url),
                'chunk_index': chunk_index,
                'content_hash': chunk_hash,
                'heading': None
            })
            chunk_index += 1
            current_chunk = para_text
        else:
            current_chunk += " " + para_text if current_chunk else para_text
    
    # Add last chunk
    if current_chunk:
        chunk_hash = generate_content_hash(current_chunk)
        chunks.append({
            'text': current_chunk.strip(),
            'source_url': url,
            'source_domain': _extract_domain(url),
            'chunk_index': chunk_index,
            'content_hash': chunk_hash,
            'heading': None
        })
    
    return chunks


def _split_large_section(text: str, heading: str, max_size: int) -> List[str]:
    """Split a large section into smaller chunks while preserving sentences."""
    chunks = []
    
    # Try to split by sentences
    sentences = text.split('. ')
    
    current_chunk = ""
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Add period back (except for last sentence if it already has one)
        if i < len(sentences) - 1 or not sentence.endswith('.'):
            sentence += '.'
        
        # If adding this sentence exceeds max, save current chunk
        if current_chunk and len(current_chunk) + len(sentence) > max_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Add last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text]


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    return urlparse(url).netloc


if __name__ == "__main__":
    # Test with a sample HTML
    test_html = """
    <main>
        <h1>Main Title</h1>
        <p>Introduction paragraph.</p>
        
        <h2>Section 1</h2>
        <p>Content for section 1.</p>
        <p>More content for section 1.</p>
        
        <h2>Section 2</h2>
        <p>Content for section 2.</p>
        
        <h3>Subsection 2.1</h3>
        <p>Content for subsection.</p>
    </main>
    """
    
    chunks = chunk_by_headings(test_html, "http://test.com")
    
    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}:")
        print(f"  Heading: {chunk.get('heading', 'None')}")
        print(f"  Text: {chunk['text'][:100]}...")
