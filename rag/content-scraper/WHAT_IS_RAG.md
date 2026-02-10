# What is RAG?

## RAG Explained

RAG = Retrieval-Augmented Generation

Instead of letting an AI make up answers, RAG retrieves real information first, then generates accurate responses based on that data.

**Without RAG:** AI generates answers from training data (may hallucinate)  
**With RAG:** AI retrieves relevant information from your database, then answers based on facts

**Example:**
- Without RAG: "The internship lasts 6 months" (guessing)
- With RAG: "According to HTWG website: 20 weeks (minimum 95 days)" (accurate)

---

## How to Use This System

### Setup
```bash
pip install -r requirements.txt
docker compose up -d
cp .env.example .env
```

### Configure
Edit `.env` file with your URLs and Qdrant settings
```env
SOURCE_URLS=https://example.com/page1,https://example.com/page2
```

### Ingest Data
```bash
python ingest_data.py                         # First run: loads all data
python ingest_data.py                         # Subsequent runs: only adds new content
```

This scrapes websites, creates embeddings, and stores them in Qdrant.

### Test
```bash
python test_retrieval.py "your question"
```

---

## n8n Integration

### Native n8n (Recommended)

Add two nodes to your workflow:

**1. Vector Store Qdrant (as Tool)**
- Mode: "Connect to Qdrant and Make Available as Tool"
- Collection: Your collection name from `.env`
- URL: (your Qdrant URL)

**2. AI Agent**
- Connect Vector Store as Tool
- Connect Ollama/OpenAI as Language Model
- Prompt: "Use the Vector Store tool to find information and answer: {{ $json.question }}"

The AI automatically:
1. Searches the vector database for relevant information
2. Uses that information to generate accurate answers

---

## How It Works

**1. Ingestion**
```
Website Text -> Split into Chunks -> Convert to Vectors -> Store in Qdrant
```

**2. Retrieval**
```
Question -> Convert to Vector -> Find Similar Vectors -> Return Relevant Text
```

**3. Generation**
```
Retrieved Information + Question -> AI -> Answer
```

---

## Key Points

- Run `python ingest_data.py` when your website content changes
- Start with Top K = 3, increase if answers need more context
- Delta loading automatically skips duplicate content on subsequent runs
- n8n connects directly to Qdrant (no API server needed)

## Struggles during Development

- **Delta Loading**: Implementing content hashing to skip duplicates was tricky but essential for efficiency.
- **Embedding Consistency**: Ensuring the same embedding model is used for both ingestion and retrieval to maintain accuracy.
- **Response Quality**: Custom chunking strategy (chunk by headings) & model choice (mxbai-embed-large) significantly improved retrieval relevance and answer quality.
