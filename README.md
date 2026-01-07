# Dify + GraphRAG + YugabyteDB Knowledge Graph Integration

A complete integration of knowledge graph capabilities with Dify.ai, powered by YugabyteDB for distributed graph storage, enabling semantic search, entity extraction, and graph visualization for enhanced AI workflows.

## Features

- **YugabyteDB Integration**: Distributed, PostgreSQL-compatible graph storage with built-in vector support
- **Document Processing API**: Extract text from PDFs, DOCX, and plain text files
- **GraphRAG API**: Build and query knowledge graphs with semantic search
- **Embedding Worker**: Automatic background generation of embeddings for semantic search
- **Graph Visualization**: Interactive web interface to visualize your knowledge graph
- **Dify Integration**: Seamlessly integrate with Dify workflows via HTTP endpoints
- **Scalable Architecture**: Horizontally scalable graph storage with YugabyteDB's distributed design

## Prerequisites

- Docker and Docker Compose installed
- Git
- 4GB+ RAM recommended
  
## Quick Start

To get started locally with Docker, including Dify.ai and a single node YugabyteDB instance, you can follow these few simple steps once this repository is cloned locally:

```
git clone https://github.com/langgenius/dify.git ./dify
cp ./dify/docker/.env.example .env
docker-compose up --build
```

This will download and deploy the latest Dify.ai Docker compose manifest as part of the manifest for this repository, which includes the APIs and worker used by the workflow in Dify.ai. All of the containers will be deployed into the same default Docker network.

## Detailed Setup

A more detailed setup process is explained below. This isn't necessary if you've followed the Quick Start approach. If you'd like to setup YugabyteDB outside Docker you can [get started here](https://www.yugabyte.com/download/).

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
# Download and install YugabyteDB (2025.1 or 2025.2)
wget https://software.yugabyte.com/releases/2025.2.0.0/yugabyte-2025.2.0.0-b131-darwin-x86_64.tar.gz
tar xvfz yugabyte-2025.2.0.0-b131-darwin-x86_64.tar.gz && cd yugabyte-2025.2.0.0/
./bin/yugabyted start
```

### 3. Build and Run Services

Ensure this repository has been cloned to a local path and then build each service with Docker:

```bash
# Build doc-processor
cd doc-processor
docker build -t doc-processor .

# Build graphrag-api
cd ../graphrag-api
docker build -t graphrag-api .

# Build visualisation
cd ../visualisation
docker build -t visualisation .

# Build embedding-worker
cd ../embedding-worker
docker build -t embedding-worker .

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

### 4. Initialize YugabyteDB Database

Connect to your YugabyteDB instance and create the graph schema:

#### For Docker YugabyteDB:

```bash
# Copy SQL file into container
docker cp yugabytedb/init-db.sql yugabyte:/tmp/

# Execute the SQL
docker exec -it yugabyte bin/ysqlsh -h localhost -f /tmp/init-db.sql
```

#### For YugabyteDB Cloud or Local Install:

```bash
# Using ysqlsh
ysqlsh -h your-host -p 5433 -U yugabyte -d yugabyte -f yugabytedb/init-db.sql

# Or using psql (YugabyteDB is PostgreSQL-compatible)
psql -h your-host -p 5433 -U yugabyte -d yugabyte -f yugabytedb/init-db.sql
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

## Configuration

### Update YugabyteDB Credentials

Edit the following files with your YugabyteDB host and / or credentials:

1. **`graphrag-api/app.py`** - Update the `DB` dictionary (lines 9-15)
2. **`embedding-worker/embedding-worker.py`** - Update the `DB` dictionary (lines 5-11)
3. **`embedding-worker/add_embeddings.py`** - Update the `DB` dictionary (lines 5-11) 
4. **`visualisation/visualise.htm`** - Update the `API_URL` constant (line 569)

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

## API Endpoints

The graphrag-api container provides several custom Flask-based REST APIs which the Dify.ai workflow uses to demonstrate a GraphRAG solution.

### Doc Processor (port 5006)

- `GET /health` - Health check
- `POST /extract/pdf` - Extract text from PDF (multipart/form-data)
- `POST /extract/docx` - Extract text from Word doc (multipart/form-data)
- `POST /extract/text` - Extract text from plain text (multipart/form-data)

### GraphRAG API (port 5005)

- `GET /health` - Health check with graph stats
- `POST /graph/search` - Keyword-based search
- `POST /graph/semantic-search` - Vector similarity search
- `POST /graph/batch-insert` - Insert entities and relationships
- `POST /graph/batch-insert-with-embeddings` - Insert with embeddings
- `POST /graph/add-embeddings-to-existing` - Add embeddings to existing nodes
- `GET /graph/visualize` - Get graph data for visualization
- `POST /graph/deduplicate` - Merge duplicate entities

## Using in Dify workflows

### 1. Extract Text from document

**HTTP Request Node Configuration:**
- URL: `http://doc-processor:5006/extract/pdf`
- Method: `POST`
- Body Type: `Form Data`
- File Field: `file`

### 2. Insert Entities into graph

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

### 3. Semantic search

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

## Graph Visualization

View your knowledge graph in a web interface:

```bash
cd graphrag-api

# Start HTTP server in background
python3 -m http.server 8080 > /dev/null 2>&1 &

# Open in browser
open http://localhost:8080/visualize.html
```

The visualization fetches data from `http://localhost:5005/graph/visualize`.

## Testing

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

## Troubleshooting

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

## Architecture

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgments

- [YugabyteDB](https://www.yugabyte.com/) - Distributed SQL database for graph storage
- [Dify.ai](https://dify.ai) - Open-source LLM app development platform
- [sentence-transformers](https://www.sbert.net/) - Embedding generation
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search extension

## Support

For issues and questions:
- Open an issue on GitHub
- Check the [Dify documentation](https://docs.dify.ai)
