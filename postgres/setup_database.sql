-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop the documents table if it exists
DROP TABLE IF EXISTS documents;

-- Create the documents table with added tsvector column
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    context TEXT,
    source TEXT,
    embedding VECTOR(1536),
    content_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- ADD INDECES FOR SEARCH
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_ip_ops);
CREATE INDEX IF NOT EXISTS documents_content_tsv_idx ON documents USING GiST (content_tsv);

-- SIMILARITY SEARCH
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

-- HYBRID SEARCH
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    limit_num INT,
    k INTEGER DEFAULT 60
)
RETURNS TABLE(id INT, content TEXT, context TEXT, source TEXT, rrf_score FLOAT8) AS $$
BEGIN
    RETURN QUERY
    WITH vector_scores AS (
        SELECT 
            id,
            content,
            context,
            source,
            ROW_NUMBER() OVER (ORDER BY -(embedding <#> query_embedding) DESC) as vector_rank
        FROM documents
    ),
    text_scores AS (
        SELECT 
            id,
            content,
            context,
            source,
            ROW_NUMBER() OVER (ORDER BY ts_rank_bm25(content_tsv, to_tsquery('english', query_text)) DESC) as text_rank
        FROM documents
        WHERE content_tsv @@ to_tsquery('english', query_text)
    )
    SELECT 
        v.id,
        v.content,
        v.context,
        v.source,
        (1.0 / (k + v.vector_rank) + 1.0 / (k + COALESCE(t.text_rank, 1000000))) as rrf_score
    FROM vector_scores v
    LEFT JOIN text_scores t ON v.id = t.id
    ORDER BY rrf_score DESC
    LIMIT limit_num;
END;
$$ LANGUAGE plpgsql;