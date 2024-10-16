#!/bin/bash
set -e

echo "Starting init-db.sh script"
# Wait for the database to be ready
timeout=120
host="db"
for i in $(seq 1 $timeout); do
  if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\l' >/dev/null 2>&1; then
    echo "Postgres is up - executing command"
    break
  fi
  echo "Postgres is unavailable - (attempt $i/$timeout)"
  sleep 1
done

if [ $i -eq $timeout ]; then
  echo "Timeout waiting for Postgres to start - POSTGRES INIT FAIL!"
  exit 1
fi

# Check if the setup_database.sql file exists
if [ -f "/app/setup_database.sql" ]; then
    echo "setup_database.sql file found"
else
    echo "setup_database.sql file not found"
    exit 1
fi

# Create the pgvector extension and set up the database tables
echo "Executing setup_database.sql"
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/setup_database.sql
echo "Finished executing setup_database.sql"

# Verify that the documents table was created
echo "Verifying documents table creation"
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'documents');"

echo "Listing all tables in the database"
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"

echo "init-db.sh script completed"

# Execute the command passed to the script
exec "$@"
