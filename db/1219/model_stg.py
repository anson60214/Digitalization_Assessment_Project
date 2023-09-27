import sqlalchemy

from sqlalchemy import Table, Column, ForeignKey, MetaData, Boolean, Integer, NUMERIC, String, BLOB, JSON

meta = MetaData(schema='stg')

dim_qualitative_question = Table('dim_qualitative_question', meta, 
    Column('question_id', String),
    Column('aspect', String),
    Column('module', String),
    Column('ind_tagging', String),
    Column('capability', String),
    Column('topic', String),
    Column('question', String),
    Column('basic', String),
    Column('advanced', String),
    Column('best_in_class', String),
    Column('updated_date', String)
)

dim_quantative_index = Table('dim_quantative_index', meta,
    Column('fin_indicator_id', String),
    Column('fin_indicator_text_en', String),
    Column('fin_indicator_text_ch', String),
    Column('fin_indicator_purpose', String),
    Column('purpose_description', String),
    Column('sensitive_variable_proportion', String),
    Column('fin_indicator_formula', String),
    Column('fin_indicator_description', String),
    Column('form_question_title', String),
    Column('form_helper_text', String),
    Column('updated_date', String)
)

dim_solution = Table('dim_solution', meta,
    Column('solution_id', String),
    Column('industry_category', String),
    Column('level1', String),
    Column('level2', String),
    Column('level3', String),
    Column('solution_description', String),
    Column('reference', String),
    Column('url1', String),
    Column('url2', String),
    Column('url3', String),
    Column('updated_date', String)
)

dim_company = Table('dim_company', meta,
    Column('company_id', String),
    Column('company_text', String),
    Column('client_text', String),
    Column('client_title', String),
    Column('capital_max', NUMERIC),
    Column('capital_min', NUMERIC),
    Column('registered_area', String),
    Column('registered_contry', String),
    Column('company_description', String),
    Column('company_year', String),
    Column('employee_max', NUMERIC),
    Column('employee_min', NUMERIC),
    Column('industry_type_l', String),
    Column('industry_type_m', String),
    Column('industry_type_s', String),
    Column('updated_date', String)
)

# dim_strategy = Table('dim_strategy', meta,
#     Column('strategy_id', String),
#     Column('strategy_text', String),
#     Column('check_detail_1', String),
#     Column('check_detail_2', String),
#     Column('check_detail_3', String),
#     # Column('aspect_ux', NUMERIC),
#     # Column('aspect_mfg', NUMERIC),
#     # Column('aspect_ppl', NUMERIC),
#     # Column('aspect_tech', NUMERIC),
#     # Column('updated_date', String)
# )

dim_industry = Table('dim_industry', meta, 
    Column('industry_id', String),
    Column('version', String),
    Column('industry_text', String),
    Column('industry_description', String),
    Column('industry_transformation_keypoint', String),
    Column('industry_transformation_advice', String),
    Column('updated_date', String)
)

dim_solution_case = Table('dim_solution_case', meta,
    Column('industry_id', String),
    Column('caseid', String),
    Column('case_text', String),
    Column('case_description', String),
    Column('case_img', BLOB),
    Column('case_link1', String),
    Column('case_link2', String),
    Column('case_link3', String),
    Column('updated_date', String)
)

dim_strategy_weight = Table('dim_strategy_weight', meta,
    Column('strategy_id', String),
    Column('aspect_ux', NUMERIC),
    Column('aspect_mfg', NUMERIC),
    Column('aspect_ppl', NUMERIC),
    Column('aspect_tech', NUMERIC),
    Column('updated_date', String)
)

financial_trend_index = Table('financial_trend_index', meta,
    Column('financial_id', String),
    Column('growth_id', String),
    Column('growth_text', String),
    Column('formula', String),
    Column('rank', NUMERIC),
    Column('updated_date', String)
)

dim_sq_relation_score = Table('dim_sq_relation_score', meta,
    Column('solution_id', String),
    Column('question_id', String),
    Column('correlation_score', NUMERIC)
)

quantative_relation_Score = Table('quantative_relation_Score', meta,
    Column('quan_relation_id', String),
    Column('financial_id', String),
    Column('version_solution', String),
    Column('solution_id', String),
    Column('Score', NUMERIC)
)

dim_version = Table('dim_version', meta,
    Column('version_id', String),
    Column('qualitative_question_form', String),
    Column('fin_question_form', String),
    Column('model_fin_question', String),
    Column('profile_question', String),
    Column('include_solution', String),
    Column('file_template', String),
    Column('update_date', String)
)

dim_sf_relation_score = Table('dim_sf_relation_score', meta,
    Column('solution_id', String),
    Column('fin_indicator_id', String),
    Column('correlation_score', NUMERIC),
    Column('updated_date', String)
    )

dim_financial_trend_index = Table('dim_financial_trend_index', meta,
    Column('fin_indicator_id', String),
    Column('trend_name', String),
    Column('trend_formula', String),
    Column('trend_score', String),
    Column('description_text', String),
    Column('updated_date', String) 
    )