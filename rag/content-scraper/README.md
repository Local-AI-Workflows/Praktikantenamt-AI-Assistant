# Content Scraping & Vector Storage System

A minimal, flexible system for scraping web content, creating embeddings, and storing them in Qdrant vector database. Features delta loading to avoid duplicate data.

## 🎯 Features

- ✅ **Multi-URL Support** - Scrape content from multiple websites
- ✅ **Flexible Configuration** - All settings via `.env` file
- ✅ **Multiple Embedding Backends** - Support for Sentence Transformers and Ollama
- ✅ **Delta Loading** - Automatically skips duplicate content
- ✅ **Duplicate Detection** - Uses content hashing to identify duplicates
- ✅ **Semantic Search** - Find relevant content using embeddings
- ✅ **German Language Support** - Optimized for German content

## 📦 What's Included

- `ingest_data.py` - Scrape, embed, and store content
- `test_retrieval.py` - Test semantic search
- `retrieve.py` - Simple retrieval interface
- `config.py` - Configuration loader
- `embeddings.py` - Unified embedding interface (Sentence Transformers & Ollama)
- `docker-compose.yml` - Qdrant database setup
- `requirements.txt` - Python dependencies

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Start Qdrant

```bash
docker compose up -d
```

### 3. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Ingest Data

```bash
# First run (creates collection)
python ingest_data.py

# Subsequent runs (delta loading - only new content)
python ingest_data.py

# Force recreate (delete and start fresh)
python ingest_data.py --force
```

### 5. Test Retrieval

```bash
# Single query
python test_retrieval.py "Wie lange dauert das Praxissemester?"

# Run test suite
python test_retrieval.py --test
```

## ⚙️ Configuration

Edit `.env` file:

```env
# Qdrant Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
COLLECTION_NAME=my_collection

# Embedding Backend
# Options: "sentence-transformers" or "ollama"
EMBEDDING_BACKEND=sentence-transformers

# Sentence Transformers Configuration (used when EMBEDDING_BACKEND=sentence-transformers)
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Ollama Configuration (used when EMBEDDING_BACKEND=ollama)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Multiple URLs (comma-separated)
SOURCE_URLS=https://example.com/page1,https://example.com/page2
```

### Embedding Backends

#### Sentence Transformers (Default)
- **Pros:** Fast, runs locally, no external service needed
- **Cons:** Limited to pre-trained models
- **Best for:** Quick setup, offline usage

```env
EMBEDDING_BACKEND=sentence-transformers
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

#### Ollama
- **Pros:** Flexible model choice, can use larger models, self-hosted
- **Cons:** Requires Ollama server running
- **Best for:** Custom models, advanced use cases

```env
EMBEDDING_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
```

Popular Ollama embedding models:
- `nomic-embed-text` - Good general-purpose model
- `mxbai-embed-large` - Higher quality, larger
- `all-minilm` - Fast and lightweight

## 📊 How Delta Loading Works

When you run `ingest_data.py` multiple times:

1. **First Run:**
   - Fetches all content
   - Creates embeddings
   - Stores in Qdrant
   - Example: 50 chunks stored

2. **Second Run (no changes):**
   - Fetches content again
   - Compares content hashes
   - Finds 50 duplicates
   - **Skips uploading** (0 new chunks)
   - ✅ Fast and efficient!

3. **Second Run (with changes):**
   - Website updated with new info
   - Finds 50 old + 5 new chunks
   - Skips 50 duplicates
   - **Uploads only 5 new chunks**
   - ✅ Incremental updates!

### How Duplicates Are Detected

- Each chunk gets a SHA-256 hash of its content
- Hash is stored in Qdrant payload
- On subsequent runs, existing hashes are fetched
- New content is compared against existing hashes
- Only new/changed content is uploaded

## 🔍 Duplicate Handling Example

### Scenario: Running ingest twice

```bash
# First run
$ python ingest_data.py
Fetching content from 1 URL(s)...
  ✓ Fetched 7513 characters
Chunking content...
  ✓ Total chunks: 19
Creating embeddings...
  ✓ Created 19 embeddings
Uploading 19 new chunks to Qdrant...
  ✓ Upload complete!

# Second run (same content)
$ python ingest_data.py
Fetching content from 1 URL(s)...
  ✓ Fetched 7513 characters
Checking for existing content (delta loading)...
  Found 19 existing chunks in database
Chunking content...
  ✓ Total chunks: 19
Creating embeddings...
  ✓ Created 19 embeddings
  ℹ Skipped 19 duplicate chunks (already in database)
  ℹ No new chunks to upload (all content already exists)
```

### Scenario: Website updated

```bash
# Website added new section
$ python ingest_data.py
Fetching content from 1 URL(s)...
  ✓ Fetched 8200 characters  # More content!
Checking for existing content (delta loading)...
  Found 19 existing chunks in database
Chunking content...
  ✓ Total chunks: 23  # 4 new chunks
Creating embeddings...
  ✓ Created 23 embeddings
  ℹ Skipped 19 duplicate chunks
Uploading 4 new chunks to Qdrant...
  ✓ Upload complete!
Total vectors in database: 23
```

## 📁 Project Structure

```
content_retrieval/
├── .env                    # Your configuration (create from .env.example)
├── .env.example           # Example configuration
├── config.py              # Configuration loader
├── embeddings.py          # Unified embedding interface
├── ingest_data.py         # Main ingestion script
├── retrieve.py            # Simple retrieval script
├── test_retrieval.py      # Test semantic search
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Qdrant setup
└── README.md              # This file
```

## 🧪 Testing

### Test Single Query
```bash
python test_retrieval.py "Wie lange dauert das Praxissemester?"
```

### Test Multiple Queries
```bash
python test_retrieval.py --test
```

### View Database Contents
```bash
# Via API
curl http://localhost:6333/collections/htwg_knowledge_base

# Via Dashboard
open http://localhost:6333/dashboard
```

## 🦙 Using Ollama for Embeddings

If you want to use Ollama instead of Sentence Transformers:

### 1. Install Ollama

```bash
# On Linux
curl -fsSL https://ollama.com/install.sh | sh

# On macOS
brew install ollama

# On Windows
# Download from https://ollama.com/download
```

### 2. Start Ollama

```bash
ollama serve
```

### 3. Pull an Embedding Model

```bash
# Recommended: nomic-embed-text
ollama pull nomic-embed-text

# Or try alternatives:
ollama pull mxbai-embed-large
ollama pull all-minilm
```

### 4. Update .env

```env
EMBEDDING_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
```

### 5. Run Ingestion

```bash
python ingest_data.py
```

**Note:** When switching between backends (Sentence Transformers ↔ Ollama), use `--force` to recreate the collection, as embeddings from different models have different dimensions and are not compatible:

```bash
python ingest_data.py --force
```

## 🔧 Advanced Usage

### Add Multiple URLs

Edit `.env`:
```env
SOURCE_URLS=https://site1.com/page1,https://site2.com/page2,https://site3.com/page3
```

### Change Chunk Size

Edit `.env`:
```env
CHUNK_SIZE=700        # Larger chunks
CHUNK_OVERLAP=100     # More overlap
```

### Use Different Embedding Model

#### For Sentence Transformers:
```env
EMBEDDING_BACKEND=sentence-transformers
# Better quality, but slower and larger
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
```

#### For Ollama:
```bash
# Pull different model
ollama pull mxbai-embed-large

# Update .env
EMBEDDING_BACKEND=ollama
OLLAMA_MODEL=mxbai-embed-large
```

**Important:** After changing embedding models, recreate the collection:
```bash
python ingest_data.py --force
```

### Force Recreate Collection

```bash
# Delete and recreate from scratch (no delta loading)
python ingest_data.py --force
```

## 🐛 Troubleshooting

### "Connection refused"
→ Start Qdrant: `docker compose up -d`

### "Collection not found"
→ Run ingestion first: `python ingest_data.py`

### "No results found"
→ Check if data was ingested: `curl http://localhost:6333/collections`

### Slow ingestion
→ Reduce chunk size or use faster model in `.env`

## 💡 Tips

1. **First Run:** Use `--force` to ensure clean start
2. **Regular Updates:** Run without `--force` for delta loading
3. **Multiple Sources:** Add all URLs in `.env` separated by commas
4. **Monitor Quality:** Use `test_retrieval.py --test` to check search quality
5. **Tune Parameters:** Adjust `CHUNK_SIZE` based on your content

## 📊 Performance

- **Ingestion:** ~2-3 minutes for 50 chunks (first run)
- **Delta Loading:** ~30 seconds if no changes (subsequent runs)
- **Search:** <100ms per query
- **Disk Space:** ~10MB per 1000 vectors

## 🔄 Workflow

```
1. Edit .env with your URLs
     ↓
2. Run: python ingest_data.py
     ↓
3. Test: python test_retrieval.py "your question"
     ↓
4. Use in your application (n8n, API, etc.)
     ↓
5. When website updates: Run step 2 again (delta loading!)
```

## 📝 License

MIT

## 🆘 Support

- Check API: `curl http://localhost:6333/collections`
- Check logs: `docker compose logs qdrant`
- View dashboard: `http://localhost:6333/dashboard`
