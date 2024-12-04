-- Create extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create CONVERSATION_ROLE enum
CREATE TYPE CONVERSATION_ROLE AS ENUM ('user', 'assistant', 'system');

-- Create the documents table with added tsvector column
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    context TEXT,
    content TEXT,
    source TEXT,
    embedding VECTOR(1536),
    content_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL CHECK (length(password) >= 8),
    verified BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    conversation_role CONVERSATION_ROLE NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- create llm_calls table
CREATE TABLE IF NOT EXISTS llm_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL,
    message_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

-- CREATE MODELS TABLE
CREATE TABLE IF NOT EXISTS models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    input_token_cost FLOAT,
    output_token_cost FLOAT
);

-- ADD INDECES FOR SEARCH
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_ip_ops);
CREATE INDEX IF NOT EXISTS documents_content_tsv_idx ON documents USING GiST (content_tsv);

-- Add index for faster message retrieval by conversation with timestamp ordering
CREATE INDEX IF NOT EXISTS messages_conversation_id_created_at_idx 
    ON messages(conversation_id, created_at);

-- Add after other indices
CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);

--------- FUNCTIONS ---------

-- SIMILARITY SEARCH FUNCTION
CREATE OR REPLACE FUNCTION similarity_search(
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

-- FULL TEXT SEARCH
CREATE OR REPLACE FUNCTION fts_search(
    query_text TEXT,
    limit_num INT
)
RETURNS TABLE(id INT, content TEXT, context TEXT, source TEXT, rank FLOAT8) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        documents.id, 
        documents.content, 
        documents.context, 
        documents.source, 
        ts_rank(documents.content_tsv, to_tsquery('english', query_text))::double precision AS rank
    FROM documents
    WHERE documents.content_tsv @@ to_tsquery('english', query_text)
    ORDER BY rank DESC
    LIMIT limit_num;
END;
$$ LANGUAGE plpgsql;

-- HYBRID SEARCH
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    limit_num INT,
    k INTEGER DEFAULT 60,
    semantic_weight FLOAT DEFAULT 0.5,
    fts_weight FLOAT DEFAULT 0.5
)
RETURNS TABLE(id INT, content TEXT, context TEXT, source TEXT, rrf_score FLOAT8) AS $$
BEGIN
    RETURN QUERY
    WITH vector_scores AS (
        SELECT 
            documents.id,
            documents.content,
            documents.context,
            documents.source,
            ROW_NUMBER() OVER (ORDER BY -(documents.embedding <#> query_embedding) DESC) as vector_rank
        FROM documents
    ),
    text_scores AS (
        SELECT 
            documents.id,
            documents.content,
            documents.context,
            documents.source,
            ROW_NUMBER() OVER (ORDER BY ts_rank(documents.content_tsv, to_tsquery('english', query_text)) DESC) as text_rank
        FROM documents
        WHERE documents.content_tsv @@ to_tsquery('english', query_text)
    )
    SELECT 
        v.id,
        v.content,
        v.context,
        v.source,
        (semantic_weight * 1.0 / (k + v.vector_rank) + 
         fts_weight * 1.0 / (k + COALESCE(t.text_rank, 1000000))) as rrf_score
    FROM vector_scores v
    LEFT JOIN text_scores t ON v.id = t.id
    ORDER BY rrf_score DESC
    LIMIT limit_num;
END;
$$ LANGUAGE plpgsql;

-- Get conversation history function
CREATE OR REPLACE FUNCTION get_conversation_history(
    _conversation_id UUID,
    _message_limit INTEGER
)
RETURNS TABLE(
    id UUID,
    conversation_role CONVERSATION_ROLE,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.conversation_role,
        m.content,
        m.created_at
    FROM messages m
    WHERE m.conversation_id = _conversation_id
    ORDER BY m.created_at
    LIMIT _message_limit;
END;
$$ LANGUAGE plpgsql;

-- Get all messages for a specific conversation
CREATE OR REPLACE FUNCTION get_conversation(
    _conversation_id UUID
)
RETURNS TABLE(
    message_id UUID,
    conversation_role CONVERSATION_ROLE,
    content TEXT,
    message_type TEXT,
    prompt TEXT,
    response TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    (
        -- Get all messages
        SELECT 
            m.id as message_id,
            m.conversation_role,
            m.content,
            NULL as message_type,
            NULL as prompt,
            NULL as response,
            NULL as model,
            NULL as input_tokens,
            NULL as output_tokens,
            NULL as cost,
            m.created_at
        FROM messages m
        WHERE m.conversation_id = _conversation_id
        
        UNION ALL
        
        -- Get all LLM calls
        SELECT 
            l.message_id,
            NULL as conversation_role,
            NULL as content,
            l.message_type,
            l.prompt,
            l.response,
            l.model,
            l.input_tokens,
            l.output_tokens,
            l.cost,
            l.created_at
        FROM llm_calls l
        WHERE l.message_id IN (SELECT id FROM messages WHERE conversation_id = _conversation_id)
    )
    ORDER BY created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate token cost based on model name, input tokens, and output tokens
CREATE OR REPLACE FUNCTION calculate_token_cost(
    model_name TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER
)
RETURNS FLOAT AS $$
DECLARE
    input_cost FLOAT;
    output_cost FLOAT;
    total_cost FLOAT;
BEGIN
    -- Query the models table to get the input and output token costs
    SELECT 
        input_token_cost,
        output_token_cost
    INTO input_cost, output_cost
    FROM models
    WHERE name = model_name;

    -- Check if the model exists
    IF input_cost IS NULL OR output_cost IS NULL THEN
        RAISE EXCEPTION 'Model not found: %', model_name;
    END IF;

    -- Calculate the total cost
    total_cost := (input_cost * input_tokens) + (output_cost * output_tokens);

    RETURN total_cost;
END;
$$ LANGUAGE plpgsql;

-- Modify the calculate_token_cost trigger function to work with llm_calls
CREATE OR REPLACE FUNCTION calculate_llm_call_cost()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate and set the cost using the calculate_token_cost function
    NEW.cost := calculate_token_cost(
        NEW.model,
        NEW.input_tokens,
        NEW.output_tokens
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop and recreate the trigger correctly
DROP TRIGGER IF EXISTS set_llm_call_cost ON llm_calls;
CREATE TRIGGER set_llm_call_cost
    BEFORE INSERT ON llm_calls
    FOR EACH ROW
    EXECUTE FUNCTION calculate_llm_call_cost();

-- INITIAL DATA INSERTION --

INSERT INTO users (email, password) 
VALUES ('trevorkinsey@gmail.com', 'ultimaterulesrag');

INSERT INTO models (name, input_token_cost, output_token_cost) VALUES
    ('gpt-4o-mini', 0.15/1e6, 0.6/1e6),
    ('gpt-4o-2024-08-06', 2.5/1e6, 10/1e6),
    ('claude-3-5-haiku-20241022', 0.25/1e6, 1.25/1e6),
    ('claude-3-5-sonnet-20241022', 3/1e6, 15/1e6),
    ('llama3.1-70b', 0/1e6, 0/1e6),
    ('llama3.1-8b', 0/1e6, 0/1e6);