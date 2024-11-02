from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class DBFunctionUpdater:

    def __init__(self):
        self.db_settings = {
            "dbname": os.getenv('POSTGRES_DB'),
            "user": os.getenv('POSTGRES_USER'),
            "password": os.getenv('POSTGRES_PASSWORD'),
            "host": os.getenv('POSTGRES_HOST'),
            "port": os.getenv('POSTGRES_PORT')
        }

    def update_function(self, sql_string: str = None) -> None:
        """
        Update or create a database function.
        
        Args:
            function_name: Name of the function to update
            sql_string: Optional SQL string. If not provided, uses predefined SQL from FUNCTION_DEFINITIONS
        """
        function_name = sql_string.split("CREATE OR REPLACE FUNCTION ")[1].split("(")[0]
        print(f"function_name: {function_name}")
        with psycopg2.connect(**self.db_settings) as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(sql_string)
                logger.info(f"Successfully updated function: {function_name}")
        

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    updater = DBFunctionUpdater()

    sql_str = """CREATE OR REPLACE FUNCTION similarity_search(
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
$$ LANGUAGE plpgsql;"""

    updater.update_function(sql_str)
    
  