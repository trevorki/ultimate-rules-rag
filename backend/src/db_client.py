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

    def get_conversation_history(self, conversation_uuid, message_limit):
        sql_query = "SELECT user_msg, ai_msg FROM get_conversation_history(%s, %s)"
        args = (conversation_uuid, message_limit)

        response = self.query_db_sql(sql_query, args)
        history = []
        for row in response:
            history.append({"role": "user", "content": row['user_msg']}) 
            history.append({"role": "assistant", "content": row['ai_msg']})
        return history
    
    def get_conversation(self, conversation_uuid):
        sql_query = "SELECT * FROM get_conversation(%s)"
        args = (conversation_uuid,)

        response = self.query_db_sql(sql_query, args)
        
        return response

    def add_message(
            self, 
            conversation_uuid, 
            user_msg, 
            ai_msg, 
            message_type="conversation", 
            model=None, 
            input_tokens=None, 
            output_tokens=None
        ):
        sql_query = """
        INSERT INTO messages 
        (conversation_id, user_msg, ai_msg, message_type, model, input_tokens, output_tokens) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        args = (conversation_uuid, user_msg.strip(), ai_msg.strip(), message_type, model, input_tokens, output_tokens)
        response = self.query_db_sql(sql_query, args)
        return response[0]['id'] if response else None
    
    def create_user(self, email):
        
        # check if user exists
        if self.get_user_id(email):
            print("user already exists")
            return self.get_user_id(email)
        else:
            sql_query = "INSERT INTO users (email) VALUES (%s) RETURNING id"
            args = (email,)
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
