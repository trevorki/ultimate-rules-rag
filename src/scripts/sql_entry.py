from dotenv import load_dotenv
import os
import psycopg2
import json
load_dotenv()


db_settings = {
    "dbname": os.getenv('POSTGRES_DB'),
    "user": os.getenv('POSTGRES_USER'),
    "password": os.getenv('POSTGRES_PASSWORD'),
    "host": os.getenv('POSTGRES_HOST'),
    "port": os.getenv('POSTGRES_PORT')
}

def query_db_sql(sql_query, args):
    with psycopg2.connect(**db_settings) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, args)
            conn.commit()
            # Only try to fetch if it's a SELECT query
            if sql_query.strip().upper().startswith('SELECT') or 'RETURNING' in sql_query.upper():
                columns = [desc[0] for desc in cursor.description]  # Get column names
                data = cursor.fetchall()
                result = [dict(zip(columns, row)) for row in data]
                return result
            return None
        

if __name__ == "__main__":

    sql_query = """
    SELECT * FROM users
    LIMIT 10
    """.replace("    ", "")
    args = {}

    response = query_db_sql(sql_query, args)

    print(f"Query:\n{sql_query}")
    print(f"\nResponse:")
    for row in response:
        print(f"\n{row}")

