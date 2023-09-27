from sqlalchemy import engine, create_engine, MetaData, select, Column, Integer, String, Table
import pandas as pd
from db.model_stg import *
from sqlalchemy.orm import sessionmaker

def connect(host, database, port, user, password):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user, password, host, port, database)

    conn = create_engine(url, client_encoding='utf8')
    meta = MetaData(bind=conn)

    return conn, meta

def get_session(conn: engine, base):
    base.metadata.bind = conn
    Session = sessionmaker(bind=engine)
    session = Session()

    return session

# login-----------------------------
def get_user(conn: engine, user_email: str) -> dict:
    s = select(dim_user).filter(dim_user.c.user_email == user_email)
    return pd.read_sql_query(s, conn).to_dict(orient='records')

# evaluation model-----------------------------
    # database
def get_dim_qualitative_question(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_qualitative_question.c.question_id, 
         dim_qualitative_question.c.aspect,
         dim_qualitative_question.c.module,
         dim_qualitative_question.c.question])
    return pd.read_sql_query(s, conn)


def get_dim_sq_relation(conn: engine) -> pd.DataFrame:
    s = select(dim_sq_relation_score).filter(dim_sq_relation_score.c.correlation_score != 0)
    return pd.read_sql_query(s, conn)


def get_dim_quantative_index(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_quantative_index.c.fin_indicator_id, 
         dim_quantative_index.c.fin_indicator_text_en,
         dim_quantative_index.c.fin_indicator_text_ch,         
         dim_quantative_index.c.fin_indicator_purpose,
         dim_quantative_index.c.sensitive_variable_proportion,
         dim_quantative_index.c.fin_indicator_formula,
         dim_quantative_index.c.sensitivity_performance_select_method,
         dim_quantative_index.c.use_percentage])
    return pd.read_sql_query(s, conn)


def get_dim_sf_relation_score(conn: engine) -> pd.DataFrame:
    s = select(dim_sf_relation_score)#.filter(dim_sf_relation_score.c.correlation_score != 0)
    return pd.read_sql_query(s, conn).drop(columns=['updated_date'])


def get_dim_financial_trend_index(conn: engine) -> pd.DataFrame:
    s = select(dim_financial_trend_index)
    return pd.read_sql_query(s, conn).drop(columns=['description_text', 'updated_date'])


def get_dim_solution(conn: engine) -> pd.DataFrame:
    s = select(dim_solution)
    return pd.read_sql_query(s, conn)


def get_strategy_weight(conn: engine, strategy_id: str) -> dict:
    # [{"strategy_id": "STRAT-1", "aspect_ux": "0.25", ...}]
    s = select(dim_strategy_weight).filter(dim_strategy_weight.c.strategy_id == strategy_id)
    return pd.read_sql_query(s, conn).to_dict(orient='records')


# reporting services-----------------------------

    # database
def get_dim_case(conn: engine) -> pd.DataFrame:
    s = select(dim_case)
    return pd.read_sql_query(s, conn)


def get_industries_cases(conn: engine, industry_l_id: str) -> pd.DataFrame:
    # many to many, join industries - industries_cases - cases
    s = (
        select(
            [dim_industry.c.industry_id, dim_industry.c.industry_l_text, dim_industry.c.industry_m_text, 
            dim_industry.c.industry_description, dim_industry.c.industry_transformation_keypoint, dim_industry.c.industry_transformation_advice,
            dim_case.c.case_id, dim_case.c.case_text, dim_case.c.case_description, dim_case.c.case_img_blob, dim_case.c.case_link1,dim_case.c.case_source]
         )
        .filter(dim_industry.c.industry_l_id == industry_l_id)
        .join(dim_industries_cases, dim_industry.c.industry_id == dim_industries_cases.c.industry_id)
        .join(dim_case, dim_industries_cases.c.case_id == dim_case.c.case_id)
    )

    return pd.read_sql_query(s, conn) #.drop(columns=['case_img_blob'])


def get_company_data(conn: engine, company_id: str) -> dict:
    s = select(dim_company).filter(dim_company.c.company_id == company_id)
    return pd.read_sql_query(s, conn).to_dict(orient='records')

def get_dim_report_template(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_report_template.c.report_id, 
         dim_report_template.c.report_data])
    return pd.read_sql_query(s, conn)

def get_dim_fact_qualitative(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_fact_qualitative.c.qualitative_id, 
         dim_fact_qualitative.c.project_id,
         dim_fact_qualitative.c.qualitative_value
         ])
    return pd.read_sql_query(s, conn)

def get_dim_fact_quantitative(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_fact_quantitative.c.quantitative_id, 
         dim_fact_quantitative.c.project_id,
         dim_fact_quantitative.c.quantitative_value
         ])
    return pd.read_sql_query(s, conn)


def insert_dim_fact(conn: engine, table: String, fact_proj_id: String, fact_value: JSON):

    metadata = MetaData(schema='stg')
    existing_table = Table(table, metadata, autoload=True, autoload_with=conn)
    
    Session = sessionmaker(bind=conn)
    session = Session()
    
    name_value = table.rsplit('_', 1)[-1] + "_value"
    
    #Create an instance of your class and add it to the session:
    data = {'project_id': fact_proj_id, name_value: fact_value}
    insert_stmt = existing_table.insert().values(data)
    session.execute(insert_stmt)
    session.commit()
    
    return