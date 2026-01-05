# Dify + GraphRAG + YugabyteDB Knowledge Graph Integration

A complete integration of knowledge graph capabilities with Dify.ai, powered by YugabyteDB for distributed graph storage, enabling semantic search, entity extraction, and graph visualization for enhanced AI workflows.

## 🌟 Features

- **YugabyteDB Integration**: Distributed, PostgreSQL-compatible graph storage with built-in vector support
- **Document Processing API**: Extract text from PDFs, DOCX, and plain text files
- **GraphRAG API**: Build and query knowledge graphs with semantic search
- **Embedding Worker**: Automatic background generation of embeddings for semantic search
- **Graph Visualization**: Interactive web interface to visualize your knowledge graph
- **Dify Integration**: Seamlessly integrate with Dify workflows via HTTP endpoints
- **Scalable Architecture**: Horizontally scalable graph storage with YugabyteDB's distributed design

## 📋 Prerequisites

- Docker and Docker Compose installed
- Git
- 4GB+ RAM recommended
- YugabyteDB instance (local or cloud) - [Get started here](https://www.yugabyte.com/download/)
  

## 🚀 Quick Start

### 1. Install Dify

Clone and start Dify:

```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
cp .env.example .env
docker compose up -d
```

Wait for all services to start (check with `docker ps`).

### 2. Set Up YugabyteDB

#### Option A: Run YugabyteDB in Docker (Recommended for Development)

```bash
docker run -d \
  --name yugabyte \
  --network docker_default \
  -p 5433:5433 \
  -p 7000:7000 \
  -p 9000:9000 \
  yugabytedb/yugabyte:latest \
  bin/yugabyted start --daemon=false
```

Wait for YugabyteDB to start (check health at http://localhost:7000):

```bash
# Wait for YugabyteDB to be ready
docker exec -it yugabyte bin/ysqlsh -h localhost -c "SELECT version();"
```

#### Option B: Use YugabyteDB Cloud (Recommended for Production)

1. Sign up at [YugabyteDB Cloud](https://cloud.yugabyte.com/)
2. Create a free cluster
3. Note your connection details (host, port, username, password)
4. Enable YSQL API and configure allowed IP addresses

#### Option C: Install YugabyteDB Locally

```bash
# Download and install YugabyteDB
wget https://downloads.yugabyte.com/releases/2.20.1.1/yugabyte-2.20.1.1-b1-darwin-x86_64.tar.gz
tar xvfz yugabyte-2.20.1.1-b1-darwin-x86_64.tar.gz
cd yugabyte-2.20.1.1/
./bin/yugabyted start
```

### 3. Set Up GraphRAG Components

Create the project structure:

```bash
cd ../..
mkdir difyai
cd difyai

# Create directories for each service
mkdir -p doc-processor graphrag-api embedding-worker
```

### 4. Doc Processor Service

**File: `doc-processor/app.py`**

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import docx
import io

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/extract/pdf', methods=['POST'])
def extract_pdf():
    """Extract text from PDF"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))

        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n\n"

        return jsonify({
            'text': text,
            'pages': len(pdf_reader.pages),
            'char_count': len(text)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract/docx', methods=['POST'])
def extract_docx():
    """Extract text from Word document"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        doc = docx.Document(io.BytesIO(file.read()))

        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n\n"

        return jsonify({
            'text': text,
            'paragraphs': len(doc.paragraphs),
            'char_count': len(text)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract/text', methods=['POST'])
def extract_text():
    """Extract text from plain text file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        text = file.read().decode('utf-8')

        return jsonify({
            'text': text,
            'char_count': len(text)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=True)
```

**File: `doc-processor/requirements.txt`**

```
flask
flask-cors
PyPDF2
python-docx
```

**File: `doc-processor/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
```

### 5. GraphRAG API Service

**Note**: Download the complete `app.py` from the repository (it's ~500 lines with all endpoints).

**File: `graphrag-api/requirements.txt`**

```
flask
flask-cors
psycopg2-binary
sentence-transformers
torch
```

**File: `graphrag-api/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
```

**File: `graphrag-api/setup-graph-db.sql`**

```sql
-- Create tables for graph storage
CREATE TABLE IF NOT EXISTS graph_nodes (
    id SERIAL PRIMARY KEY,
    entity_name TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    description TEXT,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS graph_edges (
    id SERIAL PRIMARY KEY,
    source_node_id INTEGER REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id INTEGER REFERENCES graph_nodes(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_node_id, target_node_id, relationship_type)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_nodes_name ON graph_nodes(entity_name);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph_nodes(entity_type);
CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_nodes_embedding ON graph_nodes USING ivfflat (embedding vector_cosine_ops);
```

### 6. Embedding Worker Service

**File: `embedding-worker/embedding-worker.py`**

```python
from sentence_transformers import SentenceTransformer
import psycopg2
import time

# Database configuration (YugabyteDB)
DB = {
    'host': 'yugabyte',  # Docker container name or 'localhost' for local install
    'port': 5433,  # YugabyteDB YSQL port
    'database': 'yugabyte',  # Default database
    'user': 'yugabyte',  # Default user
    'password': 'yugabyte'  # Update for production!
}

print("Loading embedding model (first run will download ~90MB)...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print(f"✅ Model loaded! Dimension: {model.get_sentence_embedding_dimension()}")

while True:
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        # Find nodes without embeddings
        cur.execute("""
            SELECT id, entity_name, entity_type, description 
            FROM graph_nodes 
            WHERE embedding IS NULL 
            LIMIT 10
        """)
        nodes = cur.fetchall()
        
        if not nodes:
            print("✅ All nodes have embeddings. Sleeping 30s...")
            time.sleep(30)
            continue
        
        # Generate embeddings
        for node_id, name, typ, desc in nodes:
            text = f"{name} {typ or ''} {desc or ''}"
            emb = model.encode(text, show_progress_bar=False)
            
            cur.execute("""
                UPDATE graph_nodes 
                SET embedding = %s 
                WHERE id = %s
            """, (emb.tolist(), node_id))
            
            print(f"✅ Added embedding: {name}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"📊 Batch complete: {len(nodes)} embeddings added\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(10)
```

**File: `embedding-worker/Dockerfile.embedding-worker`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --break-system-packages \
    sentence-transformers==5.2.0 \
    torch==2.9.1 \
    transformers==4.57.3 \
    psycopg2-binary==2.9.11 \
    numpy \
    scipy

COPY embedding-worker.py /app/worker.py

CMD ["python", "-u", "/app/worker.py"]
```

### 7. Build and Run Services

```bash
# Build doc-processor
cd doc-processor
docker build -t doc-processor .

# Build graphrag-api
cd ../graphrag-api
docker build -t graphrag-api .

# Build embedding-worker
cd ../embedding-worker
docker build -f Dockerfile.embedding-worker -t embedding-worker .

# Run all services on Dify's network
docker run -d \
  --name doc-processor \
  --network docker_default \
  -p 5006:5006 \
  doc-processor

docker run -d \
  --name graphrag \
  --network docker_default \
  -p 5005:5005 \
  graphrag-api

docker run -d \
  --name embedding-worker \
  --network docker_default \
  --restart unless-stopped \
  embedding-worker
```

### 8. Initialize YugabyteDB Database

Connect to your YugabyteDB instance and create the graph schema:

#### For Docker YugabyteDB:

```bash
# Copy SQL file into container
docker cp graphrag-api/setup-graph-db.sql yugabyte:/tmp/

# Execute the SQL
docker exec -it yugabyte bin/ysqlsh -h localhost -f /tmp/setup-graph-db.sql
```

#### For YugabyteDB Cloud or Local Install:

```bash
# Using ysqlsh
ysqlsh -h your-host -p 5433 -U yugabyte -d yugabyte -f graphrag-api/setup-graph-db.sql

# Or using psql (YugabyteDB is PostgreSQL-compatible)
psql -h your-host -p 5433 -U yugabyte -d yugabyte -f graphrag-api/setup-graph-db.sql
```

#### Verify Tables Created:

```bash
# Connect to YugabyteDB
docker exec -it yugabyte bin/ysqlsh -h localhost

# List tables
\dt

# Should see:
#  graph_nodes
#  graph_edges

# Check vector extension
\dx

# Should see pgvector extension
```

## 🔧 Configuration

### Update YugabyteDB Credentials

Edit the following files with your YugabyteDB credentials:

1. **`graphrag-api/app.py`** - Update the `DB` dictionary (lines 9-15)
2. **`embedding-worker/embedding-worker.py`** - Update the `DB` dictionary (lines 5-11)

**For Docker YugabyteDB:**
```python
DB = {
    'host': 'yugabyte',  # Container name on docker_default network
    'port': 5433,
    'database': 'yugabyte',
    'user': 'yugabyte',
    'password': 'yugabyte'
}
```

**For YugabyteDB Cloud:**
```python
DB = {
    'host': 'your-cluster.aws.ybdb.io',
    'port': 5433,
    'database': 'yugabyte',
    'user': 'admin',
    'password': 'your-secure-password',
    'sslmode': 'require'  # Required for cloud
}
```

**For Local YugabyteDB:**
```python
DB = {
    'host': 'localhost',
    'port': 5433,
    'database': 'yugabyte',
    'user': 'yugabyte',
    'password': ''  # No password for local dev
}
```

### Network Configuration

Ensure all containers are on the Dify network:

```bash
# Verify network connectivity
docker network inspect docker_default | grep Name

# Add containers to network if needed
docker network connect docker_default doc-processor
docker network connect docker_default graphrag
docker network connect docker_default embedding-worker
```

## 📡 API Endpoints

### Doc Processor (Port 5006)

- `GET /health` - Health check
- `POST /extract/pdf` - Extract text from PDF (multipart/form-data)
- `POST /extract/docx` - Extract text from Word doc (multipart/form-data)
- `POST /extract/text` - Extract text from plain text (multipart/form-data)

### GraphRAG API (Port 5005)

- `GET /health` - Health check with graph stats
- `POST /graph/search` - Keyword-based search
- `POST /graph/semantic-search` - Vector similarity search
- `POST /graph/batch-insert` - Insert entities and relationships
- `POST /graph/batch-insert-with-embeddings` - Insert with embeddings
- `POST /graph/add-embeddings-to-existing` - Add embeddings to existing nodes
- `GET /graph/visualize` - Get graph data for visualization
- `POST /graph/deduplicate` - Merge duplicate entities

## 🔗 Using in Dify Workflows

### 1. Extract Text from Document

**HTTP Request Node Configuration:**
- URL: `http://doc-processor:5006/extract/pdf`
- Method: `POST`
- Body Type: `Form Data`
- File Field: `file`

### 2. Insert Entities into Graph

**HTTP Request Node Configuration:**
- URL: `http://graphrag:5005/graph/batch-insert-with-embeddings`
- Method: `POST`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "entities": [
    {
      "name": "{{entity_name}}",
      "type": "{{entity_type}}",
      "description": "{{description}}"
    }
  ],
  "relationships": [
    {
      "source": "{{source_entity}}",
      "target": "{{target_entity}}",
      "type": "{{relationship_type}}",
      "weight": 1.0
    }
  ]
}
```

### 3. Semantic Search

**HTTP Request Node Configuration:**
- URL: `http://graphrag:5005/graph/semantic-search`
- Method: `POST`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "query": "{{search_query}}",
  "limit": 5
}
```

## 📊 Graph Visualization

View your knowledge graph in a web interface:

```bash
cd graphrag-api

# Start HTTP server in background
python3 -m http.server 8080 > /dev/null 2>&1 &

# Open in browser
open http://localhost:8080/visualize.html
```

The visualization fetches data from `http://localhost:5005/graph/visualize`.

## 🧪 Testing

### Test Doc Processor

```bash
# Create test PDF
echo "Test document" > test.txt

curl -X POST http://localhost:5006/extract/text \
  -F "file=@test.txt"
```

### Test GraphRAG API

```bash
# Health check
curl http://localhost:5005/health

# Insert test entity
curl -X POST http://localhost:5005/graph/batch-insert \
  -H "Content-Type: application/json" \
  -d '{
    "entities": [
      {
        "name": "Test Entity",
        "type": "concept",
        "description": "A test entity"
      }
    ],
    "relationships": []
  }'

# Semantic search
curl -X POST http://localhost:5005/graph/semantic-search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'
```

## 🐛 Troubleshooting

### YugabyteDB Connection Issues

**Check if YugabyteDB is running:**
```bash
# For Docker
docker logs yugabyte

# Check health
curl http://localhost:7000/
```

**Test connection:**
```bash
# From host
docker exec -it yugabyte bin/ysqlsh -h localhost -c "SELECT version();"

# From another container
docker exec graphrag psql -h yugabyte -p 5433 -U yugabyte -c "SELECT version();"
```

**Enable vector extension if missing:**
```bash
docker exec -it yugabyte bin/ysqlsh -h localhost -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Containers can't communicate

```bash
# Verify all containers are on the same network
docker network inspect docker_default

# Add containers to network if missing
docker network connect docker_default <container-name>
```

### Embedding generation fails

Check that the GraphRAG API has sentence-transformers installed:

```bash
docker exec graphrag pip list | grep sentence
```

If missing, rebuild the container with the correct Dockerfile.

### Plugin daemon errors in Dify

Clear corrupted plugin cache:

```bash
docker stop docker-plugin_daemon-1
sudo rm -rf dify/docker/volumes/plugin_daemon/cwd/*
docker start docker-plugin_daemon-1
```

## 📝 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Dify.ai                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web UI     │  │     API      │  │   Workers    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP Requests
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Doc Processor│    │  GraphRAG    │    │  Embedding   │
│   :5006      │    │     :5005    │    │   Worker     │
└──────────────┘    └──────────────┘    └──────────────┘
                            │                   │
                            └───────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────┐
                         │   YugabyteDB     │
                         │   (YSQL :5433)   │
                         │                  │
                         │  • Graph Nodes   │
                         │  • Graph Edges   │
                         │  • Vector Search │
                         │  • Distributed   │
                         └──────────────────┘
```

### Why YugabyteDB?

- **PostgreSQL Compatible**: Drop-in replacement with full SQL support
- **Built-in Vector Support**: Native pgvector extension for embeddings
- **Distributed**: Horizontally scalable across multiple nodes
- **High Availability**: Automatic replication and failover
- **Multi-Cloud**: Run anywhere (AWS, GCP, Azure, on-prem)
- **ACID Transactions**: Strong consistency guarantees

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [YugabyteDB](https://www.yugabyte.com/) - Distributed SQL database for graph storage
- [Dify.ai](https://dify.ai) - Open-source LLM app development platform
- [sentence-transformers](https://www.sbert.net/) - Embedding generation
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search extension

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the [Dify documentation](https://docs.dify.ai)
