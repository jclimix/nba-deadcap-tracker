import pandas as pd
from loguru import logger
import os, sys

script_dir = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(script_dir, '..')))  

from sql_utils.sql_connector import *

def insert_df_to_db(df, table_name, schema):
    try:
        engine = connect_to_db(schema)

        df.to_sql(table_name, engine, schema=schema, if_exists='replace', index=False)

        logger.info(f"Dataframe successfully inserted into schema: '{schema}' as table: '{table_name}'")

    except Exception as e:
        logger.error(f"Error inserting data: {str(e)}.")

def extract_table_to_df(table_name, schema):
    try:
        engine = connect_to_db(schema)
        
        full_table_name = f'"{schema}"."{table_name}"'
        
        df = pd.read_sql(f'SELECT * FROM {full_table_name}', engine)

        logger.info(f"Schema '{schema}': Table '{table_name}' successfully pulled into DataFrame")
        return df

    except Exception as e:
        logger.error(f"Error pulling table: {str(e)}.")
        return None


if __name__ == '__main__':
    data = {
        'name': ['LeBron James', 'Stephen Curry', 'Kevin Duranimal'],
        'team': ['Los Angeles Lakers', 'Golden State Warriors', 'Brooklyn Nets'],
        'position': ['Forward', 'Guard', 'Forward']
    }

    pd.set_option('display.max_columns', None)

    df = pd.DataFrame(data)

    # insert_df_to_db(df, 'players', 'playoffs')

    pulled_df = extract_table_to_df('league_wins_teams', 'salary')
    if pulled_df is not None:
        print(pulled_df)
