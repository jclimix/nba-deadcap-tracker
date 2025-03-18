from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

def connect_to_db(schema=None):
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')

    conn_str = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    
    engine = create_engine(conn_str)

    if schema:
        with engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {schema}"))

    return engine
