import collections 
import collections.abc
from pptx import Presentation
from io import BytesIO
import json
import pandas as pd
from sqlalchemy import engine, create_engine, MetaData, select
from model_stg import *

def load_config(f_name: str):
    with open(f_name, mode='r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def connect(host, database, port, user, password):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user, password, host, port, database)

    conn = create_engine(url, client_encoding='utf8')
    meta = MetaData(bind=conn)

    return conn, meta

DB_INFO = load_config('db\\connection_info.json')['admin']
DB_CONNECTION, DB_META = connect(DB_INFO['host'], DB_INFO['database'], DB_INFO['port'], DB_INFO['user'], DB_INFO['password'])

def get_dim_report_template(conn: engine) -> pd.DataFrame:
    s = select(
        [dim_report_template.c.report_id, 
         dim_report_template.c.report_data])
    return pd.read_sql_query(s, conn)

pptx_template=get_dim_report_template(DB_CONNECTION)
prs = Presentation(BytesIO(pptx_template.iloc[0,1]))

prs.save("test.pptx")