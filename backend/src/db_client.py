from dotenv import load_dotenv
import os
import psycopg2
from pydantic import BaseModel
from uuid import uuid4

load_dotenv()
class DBClient(BaseModel):
    db_settings: dict = None  # Define with a default value

    def model_post_init(self, __context) -> None:
        self.db_settings = {
            "dbname": os.getenv('POSTGRES_DB'),
            "user": os.getenv('POSTGRES_USER'),
            "password": os.getenv('POSTGRES_PASSWORD'),
            "host": os.getenv('POSTGRES_HOST'),
            "port": os.getenv('POSTGRES_PORT')
        }

    def query_db_sql(self, sql_query, args):
        try:
            with psycopg2.connect(**self.db_settings) as conn:
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
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")
            raise

    def get_conversation_history(self, conversation_id, message_limit):
        sql_query = """
        SELECT * FROM get_conversation_history(%s, %s)
        """
        args = (conversation_id, message_limit)

        response = self.query_db_sql(sql_query, args)
        history = []
        for row in response:
            history.append({
                "role": row['conversation_role'],
                "content": row['content']
            })
        return history[::-1]  # Reverse to get chronological order
    
    def get_conversation(self, conversation_id):
        sql_query = """SELECT * FROM get_conversation(%s)"""
        args = (conversation_id,)
        return self.query_db_sql(sql_query, args)

    def add_message(
            self, 
            conversation_id, 
            conversation_role,
            content,
            created_at=None
        ):
        sql_query = """
        INSERT INTO messages 
        (conversation_id, conversation_role, content, created_at) 
        VALUES (%s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
        RETURNING id
        """
        args = (conversation_id, conversation_role, content.strip(), created_at)
        response = self.query_db_sql(sql_query, args)
        return response[0]['id'] if response else None

    def add_llm_call(
            self,
            message_id,
            message_type,
            prompt,
            response,
            model,
            usage
        ):
        """
        Add an LLM call to the database.
        
        Args:
            message_id: UUID of the associated message
            message_type: Type of the message (e.g., 'next_step', 'reword', 'answer', 'verify')
            prompt: The prompt sent to the LLM
            response: The response received from the LLM
            model: The model name used
            usage: Dictionary containing 'input_tokens' and 'output_tokens'
        """
        sql_query = """
        INSERT INTO llm_calls 
        (message_id, message_type, prompt, response, model, input_tokens, output_tokens) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, cost
        """
        # Ensure we're getting integer values for tokens, defaulting to 0 if not found
        input_tokens = int(usage.get('input_tokens', 0))
        output_tokens = int(usage.get('output_tokens', 0))
        
        args = (
            message_id, 
            message_type, 
            prompt.strip(), 
            response.strip(), 
            model, 
            input_tokens,
            output_tokens
        )
        
        response = self.query_db_sql(sql_query, args)
        return response[0] if response else None

    def create_user(self, email, password):
        
        # check if user exists
        if self.get_user_id(email):
            print("user already exists")
            return self.get_user_id(email)
        else:
            sql_query = "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id"
            args = (email,password,)
            response = self.query_db_sql(sql_query, args)
            return response[0]['id'] if response else None

    def get_user_id(self, email):
        sql_query = "SELECT id FROM users WHERE email = %s"
        args = (email,)
        response = self.query_db_sql(sql_query, args)
        return response[0]['id'] if response else None
    
    def change_password(self, email, new_password):
        sql_query = "UPDATE users SET password = %s WHERE email = %s"
        args = (new_password, email)
        response = self.query_db_sql(sql_query, args)
        return response
    
    def check_password(self, email, password):
        sql_query = "SELECT 1 FROM users WHERE email = %s AND password = %s"
        args = (email, password)
        response = self.query_db_sql(sql_query, args)
        if len(response) > 0:
            print("password is correct")
            return True
        else:
            print("password is incorrect")
            return False

    def create_conversation(self, user_email: str|None = None, user_id: str|None = None, conversation_id: str|None = None):
        if not user_id:
            user_id = self.get_user_id(user_email)

        conversation_id = str(uuid4()) if conversation_id is None else conversation_id
        sql_query = """
        INSERT INTO conversations (id, user_id) 
        VALUES (%s, %s) 
        RETURNING id"""
        args = (conversation_id, user_id)
        response = self.query_db_sql(sql_query, args)
        print(f"create_conversation response: {response}")
        return response[0]['id'] if response else None
    
    def calculate_token_cost(self, model_name, input_tokens, output_tokens):
        sql_query = "SELECT calculate_token_cost(%s, %s, %s)"
        args = (model_name, int(input_tokens), int(output_tokens))
        response = self.query_db_sql(sql_query, args)
        return response[0]['calculate_token_cost'] if response else None

    def calculate_conversation_cost(self, conversation_id):
        conversation = self.get_conversation(conversation_id)
        total_input_tokens = sum(message['input_tokens'] for message in conversation)
        total_output_tokens = sum(message['output_tokens'] for message in conversation)
        return self.calculate_token_cost(conversation[0]['model'], total_input_tokens, total_output_tokens)

    def verify_user_email(self, email: str) -> bool:
        sql_query = """
        UPDATE users 
        SET verified = true 
        WHERE email = %s 
        RETURNING id
        """
        args = (email,)
        response = self.query_db_sql(sql_query, args)
        return bool(response)

    def update_password(self, email: str, new_password: str) -> bool:
        try:
            sql_query = """
            UPDATE users 
            SET password = %s 
            WHERE email = %s 
            RETURNING id
            """
            args = (new_password, email)
            response = self.query_db_sql(sql_query, args)
            return bool(response)
        except Exception as e:
            print(f"Error updating password: {str(e)}")
            return False


