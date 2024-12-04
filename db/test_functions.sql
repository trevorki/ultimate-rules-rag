-- Start transaction so we can rollback all changes
BEGIN;

-- Insert test user and get their ID
WITH user_insert AS (
    INSERT INTO users (email, password) 
    VALUES ('test@example.com', 'test_password_123')
    RETURNING id
)
SELECT id INTO TEMPORARY TABLE temp_user_id FROM user_insert;

-- Create test conversation
WITH conv_insert AS (
    INSERT INTO conversations (user_id) 
    SELECT id FROM temp_user_id
    RETURNING id
)
SELECT id INTO TEMPORARY TABLE temp_conversation_id FROM conv_insert;

-- Insert test messages
WITH message_insert AS (
    INSERT INTO messages (conversation_id, conversation_role, content) 
    SELECT id, 'user', 'Hello, how are you?'
    FROM temp_conversation_id
    RETURNING id
)
SELECT id INTO TEMPORARY TABLE temp_message_id FROM message_insert;

-- Insert test llm_call
INSERT INTO llm_calls (
    message_id, 
    message_type, 
    prompt, 
    response, 
    model, 
    input_tokens, 
    output_tokens
) 
SELECT 
    id,
    'chat', 
    'Hello, how are you?', 
    'I am doing well, thank you!',
    'claude-3-5-sonnet-20241022',
    10,
    15
FROM temp_message_id;

-- Insert test documents
WITH vector_string AS (
    SELECT '[' || 
           array_to_string(
               array_cat(
                   ARRAY[0.1234, 0.2345],
                   array_cat(
                       array_fill(0::float8, ARRAY[1533]),
                       ARRAY[0.3456]
                   )
               ),
               ','
           ) || ']' AS vec
)
INSERT INTO documents (content, context, source, embedding)
SELECT 
    'This is a test document about cats',
    'pets',
    'test_source',
    vec::vector
FROM vector_string;

-- Test similarity_search
SELECT 'Testing similarity_search' as test;
WITH query_vector AS (
    SELECT '[' || 
           array_to_string(
               array_cat(
                   ARRAY[0.1, 0.2],
                   array_cat(
                       array_fill(0::float8, ARRAY[1533]),
                       ARRAY[0.3]
                   )
               ),
               ','
           ) || ']' AS vec
)
SELECT * FROM similarity_search((SELECT vec::vector FROM query_vector), 2);

-- Test fts_search
SELECT 'Testing fts_search' as test;
SELECT * FROM fts_search('cats & dogs', 2);

-- Test hybrid_search
SELECT 'Testing hybrid_search' as test;
WITH query_vector AS (
    SELECT '[' || 
           array_to_string(
               array_cat(
                   ARRAY[0.1, 0.2],
                   array_cat(
                       array_fill(0::float8, ARRAY[1533]),
                       ARRAY[0.3]
                   )
               ),
               ','
           ) || ']' AS vec
)
SELECT * FROM hybrid_search(
    'cats',
    (SELECT vec::vector FROM query_vector),
    2
);

-- Test get_conversation_history
SELECT 'Testing get_conversation_history' as test;
SELECT * FROM get_conversation_history((SELECT id FROM temp_conversation_id), 5);

-- Test get_conversation
SELECT 'Testing get_conversation' as test;
SELECT * FROM get_conversation((SELECT id FROM temp_conversation_id));

-- Test calculate_token_cost
SELECT 'Testing calculate_token_cost' as test;
SELECT calculate_token_cost('claude-3-5-sonnet-20241022', 100, 50);

-- Verify llm_call cost calculation trigger worked
SELECT 'Testing llm_call cost calculation' as test;
SELECT cost FROM llm_calls WHERE message_id = (SELECT id FROM temp_message_id);

-- ROLLBACK all changes
ROLLBACK;

-- Verify cleanup worked
SELECT 'Verifying cleanup' as test;
SELECT COUNT(*) FROM users WHERE email = 'test@example.com'; 