#!/bin/bash

# Build the Docker image
echo "Building embedding-worker image..."
docker build -f Dockerfile.embedding-worker -t embedding-worker:latest .

# Stop and remove old container if it exists
echo "Removing old container if exists..."
docker rm -f embedding-worker 2>/dev/null || true

# Run the container
echo "Starting embedding-worker container..."
docker run -d \
  --name embedding-worker \
  --network docker_default \
  --restart unless-stopped \
  embedding-worker:latest

# Show logs
echo "Container started. Showing logs..."
docker logs -f embedding-worker
