-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop the documents table if it exists
DROP TABLE IF EXISTS documents;

-- Create the documents table with a vector column for embeddings
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    context TEXT,
    source TEXT,
    embedding VECTOR(1536)  -- Adjust the dimension if necessary
);

-- Create an index on the embedding column for efficient similarity search
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_ip_ops);

-- SIMILARITY SEARCH FUNCTION
CREATE OR REPLACE FUNCTION query_similar_documents(
    query_embedding VECTOR(1536),
    limit_num INT
)
RETURNS TABLE(id INT, content TEXT, context TEXT, source TEXT, similarity FLOAT8) AS $$
BEGIN
    RETURN QUERY
    SELECT documents.id, documents.content, documents.context, documents.source, -(documents.embedding <#> query_embedding) AS similarity
    FROM documents
    ORDER BY similarity DESC
    LIMIT limit_num;
END;
$$ LANGUAGE plpgsql;

