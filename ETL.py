import logging
logger = logging.getLogger(__name__)

from db.repository_stg import insert_dim_fact, engine
import module.data_transformation as transform
import pandas as pd
import json

import base64

TEST_BASE_YEAR = '2020'

def extract_tables(content: dict) -> dict[str, pd.DataFrame]:
    
    tables_xlsx = base64.b64decode(content.pop('table_data'))

    tables: dict = {}
    tables['df_financial_data'] = pd.read_excel(tables_xlsx, sheet_name='tbl_quantitative')
    tables['df_solution_filter'] = pd.read_excel(tables_xlsx, sheet_name='tbl_solution_filter')
    tables['df_form_weight'] = pd.read_excel(tables_xlsx, sheet_name='tbl_interviewee_weight')
    tables['df_competitor'] = transform_df_competitor(pd.read_excel(tables_xlsx, sheet_name='tbl_competitor'))
    tables['df_form_data'], tables['df_company_data'] = extract_form_data(content)

    logger.debug(tables['df_competitor'])
    logger.debug(tables['df_financial_data'])
    logger.debug(tables['df_form_data'])
    logger.debug(tables['df_company_data'])

    del tables_xlsx
    return tables


def extract_form_data(raw_json: dict) -> pd.DataFrame:
    # 功能: 分離問卷資料與公司基本資料
    df_raw: pd.DataFrame = pd.DataFrame(raw_json.items()) # use key & value as two columns.
    df_raw.columns = ['description', 'value']             # rename column.

    mask = df_raw['description'].str.split('.').apply(len) == 4
    
    # 問卷資料 董事長.王小明.SERV-1.[現況]
    df_form_data = df_raw.loc[mask].copy(deep=True)
    df_form_data[['job_title', 'interviewee', 'question_id', 'attribute']] = df_form_data['description'].str.split('.', expand=True)

    # 公司基本資料 company_text.: 三發地產
    df_company_data = df_raw.loc[~mask].copy(deep=True)
    df_company_data['id'] = df_raw['description'].str.split('.', expand=True)[0]
    df_company_data['description'] = df_raw['description'].str.split('.', expand=True)[1]
    df_company_data = df_company_data.loc[(df_company_data["id"] != "FIN")] 

    return df_form_data[['job_title', 'interviewee', 'question_id', 'attribute', 'value']], df_company_data[['id', 'description', 'value']] # reorder column.


def transform_df_competitor(df_competitor: pd.DataFrame) -> pd.DataFrame:
    # 功能: report plot -> 競爭對手財務分析
    df = df_competitor.drop(columns=['名稱', '單位'])

    # for each row, multiply value column by their unit multiplier.
    value_columns: list = [column_name for column_name in df if column_name.startswith('競爭者')]
    df.loc[(~pd.isna(df.multiplier)), value_columns] = (
        df.loc[(~pd.isna(df.multiplier)), value_columns]
        .apply(lambda column: column * df.multiplier, axis = 0)
    )

    df = df.drop(columns=['multiplier'])
    df = df.set_index('name_en').transpose()

    return df


def load_raw_data(conn: engine, df_form_data: pd.DataFrame, df_company_data: pd.DataFrame, df_financial_data: pd.DataFrame) -> pd.DataFrame | pd.DataFrame:
    json_form_data: json = df_form_data.to_json(orient='records')
    json_financial_data: json = df_financial_data.to_json(orient='records') 
    
    # use taxID_baseYear as current transaction id
    company_id = transform.get_form_value(df_company_data, "company_id")
    fact_project_id = str(company_id) + "_" + TEST_BASE_YEAR
    
    insert_dim_fact(conn, "dim_fact_qualitative", fact_project_id, json_form_data)
    insert_dim_fact(conn, "dim_fact_quantitative", fact_project_id, json_financial_data)
    
    return df_form_data, df_financial_data