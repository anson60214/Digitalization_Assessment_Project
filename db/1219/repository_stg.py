from sqlalchemy import engine, select
import pandas as pd
from db.model_stg import *

# def getDimStrategy(conn):
#     s = select(dim_strategy)
#     return conn.execute(s)

def get_strategy_weight(conn: engine, strategy_id: str) -> dict:
    # [{"strategy_id": "STRAT-1", "aspect_ux": "0.25", ...}]
    s = select(dim_strategy_weight).filter(dim_strategy_weight.c.strategy_id == strategy_id)
    return pd.read_sql_query(s, conn).to_dict(orient='records')


def get_dim_qualitative_question(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_qualitative_question.c.question_id, 
        dim_qualitative_question.c.aspect,
        dim_qualitative_question.c.module
        ])
    return pd.read_sql_query(s, conn)


def get_dim_sq_relation(conn: engine) -> pd.DataFrame:
    s = select(dim_sq_relation_score).filter(dim_sq_relation_score.c.correlation_score != 0)
    return pd.read_sql_query(s, conn)


def get_dim_quantative_index(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_quantative_index.c.fin_indicator_id, 
         dim_quantative_index.c.fin_indicator_text_en,
         dim_quantative_index.c.fin_indicator_purpose,
         dim_quantative_index.c.sensitive_variable_proportion,
         dim_quantative_index.c.fin_indicator_formula])
    return pd.read_sql_query(s, conn)

def get_dim_sf_relation_score(conn: engine) -> pd.DataFrame:
    s = select(dim_sf_relation_score).filter(dim_sf_relation_score.c.correlation_score != 0)
    return pd.read_sql_query(s, conn).drop(columns=['updated_date'])

def get_dim_financial_trend_index(conn: engine) -> pd.DataFrame:
    s = select(dim_financial_trend_index)
    return pd.read_sql_query(s, conn).drop(columns=['description_text', 'updated_date'])

def get_dim_solution(conn: engine) -> pd.DataFrame:
    s = select(dim_solution)
    return pd.read_sql_query(s, conn)