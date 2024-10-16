# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app/

# Make sure the script is executable
RUN chmod +x /app/init-db.sh

# # Copy the SQL file into the container
# COPY setup_database.sql /docker-entrypoint-initdb.d/setup_database.sql

# # Use init-db.sh as the entrypoint
# ENTRYPOINT ["/app/init-db.sh"]

# CMD ["python", "query_vectorstore.py"]
