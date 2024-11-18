#!/bin/bash

# Set default chunk size
CHUNK_SIZE=${1:-1000}

# Stop and remove the existing container and its volumes if they exist
echo "Stopping and removing existing containers..."
docker-compose down -v

# Build and start the containers
echo "Building and starting containers..."
docker-compose up db -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Run the vectorstore preparation script
echo "Running vectorstore preparation script..."
python prepare_vectorstore/3-add_to_vectorstore.py --chunk_size $CHUNK_SIZE

# Run the retrieval evals
echo "Running retrieval evals..."
python evals/evaluate_retrieval.py --chunk_size $CHUNK_SIZE

echo "Process completed!" 