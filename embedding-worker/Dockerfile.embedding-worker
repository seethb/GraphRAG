FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir --break-system-packages \
    sentence-transformers==5.2.0 \
    torch==2.9.1 \
    transformers==4.57.3 \
    psycopg2-binary==2.9.11 \
    requests==2.32.5 \
    numpy \
    scipy

# Copy the worker script
COPY embedding-worker.py /app/worker.py

# Run the worker
CMD ["python", "-u", "/app/worker.py"]
