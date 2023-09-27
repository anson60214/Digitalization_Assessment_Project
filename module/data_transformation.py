import logging
logger = logging.getLogger(__name__)

import pandas as pd
import numpy as np
import itertools

from module.formula_check import formula_check
from scipy.stats import rankdata

FIN_INDICATOR_INDEX: dict = {
    "固定資產周轉率 (次)" : 0,
    "應收帳款收現天數 (天)": 1,
    "應付帳款付現天數 (天)" : 2,
    "銷貨成本率 (%)" : 3,
    "存貨周轉天數 (天)" : 4,
    "營收成長率 (%)" : 5,
    "營業費用率 (%)" : 6,
    "員工生產力 (千元)" : 7
}

FIN_INDICATOR_RENAME: dict = {
    "固定資產周轉率" : "固定資產周轉率 (次)",
    "應收帳款周轉天數" : "應收帳款收現天數 (天)",
    "應付帳款周轉天數" : "應付帳款付現天數 (天)",
    "銷貨成本率" : "銷貨成本率 (%)",
    "存貨周轉天數" : "存貨周轉天數 (天)",
    "銷貨收入成長率": "營收成長率 (%)",
    "營業費用率" : "營業費用率 (%)",
    "員工生產力" : "員工生產力 (千元)"
}

# utils
def retrieve_variable(df: pd.DataFrame, key_column_name: str, value_column_name: str) -> dict:
    variables: dict = {}
    list_variable: list[dict] = df.to_dict(orient='records') # [{key_column_name: key_value, value_column_name: value}, {}]

    for row in list_variable:
        variables[row[key_column_name]] = row[value_column_name]
    
    return variables

def get_form_value(df_form_data: pd.DataFrame, key: str):
    return df_form_data.loc[(df_form_data["id"] == key), "value"].iloc[0]

# data validation -----------------------------
def check_formula(name: str, formula: str):
    result = formula_check(formula)
    if not result.isAllowed:
        raise Exception(f'{str(result.exception)} at {name}')

# evaluation model -----------------------------
def quantitative_data_cleansing(df_financial_data: pd.DataFrame, dim_fin_indicator: pd.DataFrame) -> pd.DataFrame | dict | dict:
    # (source: user input) variables -> {fin_indicator_name_en: constant}
    # (source: user input) year_data -> index: year, column: fin_indicator_name_en
    # (source: database config) formulas -> {fin_indicator_name_en: fin_indicator_formula, ...}
    # (source: database config) sensitivity_performance_select_methods -> {fin_indicator_name_en: min()/max(), ...}

    # (source: user input) variables -> {fin_indicator_name_en: constant}
    variables = retrieve_variable(df_financial_data[~df_financial_data['常數'].isnull()], 'name_en', '常數')

    # (source: user input) year_data -> index: year, column: fin_indicator_name_en
    df_year_data = 	transform_year_data(df_financial_data)
    df_year_data = df_year_data.apply(pd.to_numeric) # convert to numeric to prevent user input code injection
    
    # (source: database config) formulas -> {fin_indicator_name_en: fin_indicator_formula, ...}
    mask = ((dim_fin_indicator.fin_indicator_purpose == "module-main") | (dim_fin_indicator.fin_indicator_purpose == "sensitivity"))
    formulas = retrieve_variable(dim_fin_indicator[mask], 'fin_indicator_text_en', 'fin_indicator_formula')

    for indicator, formula in formulas.items():
        check_formula(indicator, formula) # code injection detection

    # (source: database config) sensitivity_performance_select_methods -> {fin_indicator_name_en: min()/max(), ...}
    mask = (dim_fin_indicator.fin_indicator_purpose == "sensitivity")
    temp = dim_fin_indicator[mask][['fin_indicator_text_en', 'sensitivity_performance_select_method', 'use_percentage']]
    temp['fin_indicator_text_en'] = temp.apply(lambda row: str(row['fin_indicator_text_en']).replace('_sensitivity', ''), axis=1)
    sensitivity_performance_select_methods = temp[~temp['sensitivity_performance_select_method'].isnull()].set_index('fin_indicator_text_en').to_dict(orient='index')
    
    return df_year_data, formulas, sensitivity_performance_select_methods, variables


def transform_year_data(df_financial_data: pd.DataFrame):
    df_financial_data = df_financial_data.rename(columns={'name_en': 'fin_indicator_text_en'})
    keep_column: list = [column_name for column_name in df_financial_data if column_name.startswith('20')] #choose 20xx year column
    
    # multiply year value by their unit multiplier.
    df_financial_data.loc[:, keep_column] = df_financial_data.loc[:, keep_column].apply(
        lambda column: column * df_financial_data.multiplier, axis=0
        )
    
    # generate columns to keep.
    keep_column.insert(0, 'fin_indicator_text_en')
    
    # transpose
    df_year_data = df_financial_data[keep_column].set_index('fin_indicator_text_en').transpose()
    df_year_data.index.name = 'year'
    logger.debug(df_year_data)
    #df_year_data: pd.DataFrame = np.transpose(df_financial_data.loc[:, keep_column ].set_index("fin_indicator_text_en") )
    df_year_data = df_year_data[df_year_data['previous_sales_revenue'].notna()] #.reset_index().rename(columns={'index': 'year'})
    logger.debug(df_year_data)

    return df_year_data


def summarized_form_data(df_form_data: pd.DataFrame, df_form_weight: pd.DataFrame) -> pd.DataFrame:
    # input: 
    #   form_data: 'job_title', 'interviewee', 'question_id', 'attribute', 'value'
    #   form_weight: '問卷', '權重'
    # output: 
    #   question_id, attribute, value(summarized)
    df_form_data['value'] = df_form_data['value'].apply(pd.to_numeric, errors='coerce')
    df_form_data['weight_key'] = df_form_data['job_title'] + "_" + df_form_data['interviewee']
    
    df = df_form_data.merge(df_form_weight, left_on='weight_key', right_on='問卷', how='left')
    df['value'] = df['value'] * df['權重']

    return df.groupby(['question_id', 'attribute'])['value'].sum().reset_index()


def solution_filter(df_solution_filter: pd.DataFrame) -> pd.DataFrame:
    return df_solution_filter[~pd.isnull(df_solution_filter['納入評估'])].drop(columns=['納入評估'])

# reporting services -----------------------------
# 只有在製作報表時，才會進行單位轉換。
def competitor_data(df_competitor: pd.DataFrame, df_year_data: pd.DataFrame, company_name: str) -> pd.DataFrame:
    base_year = max(df_year_data['year'].drop_duplicates())
    base_year_data: pd.DataFrame = df_year_data.loc[df_year_data.year == base_year]
    base_year_data['name_en'] = "客戶"
    base_year_data['competitor_name'] = company_name

    df = pd.concat([df_competitor, base_year_data.reset_index().set_index('name_en')], join='inner')

    logger.debug("competitor_data")
    logger.debug(df)

    return df


def industry_with_case_count(industry_cases: pd.DataFrame) -> dict:
    industry_case_count = industry_cases.value_counts(subset=['industry_id']).rename('case_count')      # calculate case count.

    industries = (industry_cases
        .drop_duplicates(subset = 'industry_id')#[['industry_id', 'industry_l_text', 'industry_m_text']] # unique industry_id
        .merge(industry_case_count, on='industry_id', how='inner').set_index('industry_id')             # calculate case count.
    ).to_dict(orient='index')

    return industries


def qualitative_top10_gap(df_qualitative_result_question: pd.DataFrame) -> dict:
    df_qualitative_result_question['gap'] = round(df_qualitative_result_question['gap'], 2)
    qualitative_gap_data: dict = df_qualitative_result_question.nlargest(10, ['gap', 'ql_score']).reset_index().astype(str).to_dict(orient='index')
    
    # extract the gap data and rank them
    # if the rank is tie, it will have the same rank. e.g. 1,2,2,3,3,3
    gap_data: list = [qualitative_gap_data[rows]["gap"] for rows in qualitative_gap_data ]
    ranks = rankdata(gap_data, method='average').astype(int)
    unique_ranks = sorted(set(ranks), reverse=True)
    rank_dict = dict(zip(unique_ranks, range(1, len(unique_ranks) + 1)))
    rankings: list = [rank_dict[r] for r in ranks]
    for rows in qualitative_gap_data:
        qualitative_gap_data[rows]["rank"] = rankings[rows]
    #print(qualitative_gap_data)
    return qualitative_gap_data


def qualitative_top3_gap(df_qualitative_result_question: pd.DataFrame, aspect1: str, aspect2: str) -> dict:
    # extract the data with 2 required aspects
    # each select top 3 gap and then concat 
    df_qualitative_result_question['gap'] = round(df_qualitative_result_question['gap'], 2)
    df_qualitative_result_question_1 = df_qualitative_result_question[df_qualitative_result_question['aspect'] == aspect1]
    df_qualitative_result_question_2 = df_qualitative_result_question[df_qualitative_result_question['aspect'] == aspect2]
    df_qualitative_result_question_1 = df_qualitative_result_question_1.nlargest(3, ['gap', 'ql_score']).astype(str)
    df_qualitative_result_question_2 = df_qualitative_result_question_2.nlargest(3, ['gap', 'ql_score']).astype(str)
    df_qualitative_result_question_mix: pd.DataFrame = pd.concat([df_qualitative_result_question_1, df_qualitative_result_question_2]).reset_index().to_dict(orient='index')
    return df_qualitative_result_question_mix


def solution_ranking(df_solution: pd.DataFrame) -> dict:
    # soultion ROI: 取 % 小數點後兩位。https://stackoverflow.com/questions/5306756/how-to-print-a-percentage-value-in-python
    df_solution.loc[:, 'ROI_formatted'] = df_solution.loc[:, 'ROI'].map('{:.2%}'.format)
    logger.debug('===========================df_solution=====================')
    logger.debug(df_solution[['level3', 'ROI', 'ROI_formatted']])
    return df_solution.reset_index().astype(str).to_dict(orient='index')


def fin_indicator_data(df_trend: pd.DataFrame) -> list[dict]:
    # 只留下製作簡報所需資料
    df_trend = df_trend[['trend_name', 'fin_indicator_text_ch', 'png_buffer', 'performance_gap_impact_cashflow', 'sensitivity_value']].copy()

    # 取整數，加千分位: https://towardsdatascience.com/apply-thousand-separator-and-other-formatting-to-pandas-dataframe-45f2f4c7ab01#:~:text=Add%20Thousand%20Comma%20Separators&text=We%20use%20the%20python%20string,'Median%20Sales%20Price'%20column.
    for column_name in ['performance_gap_impact_cashflow', 'sensitivity_value']:
        df_trend[column_name] = df_trend[column_name].round(0)
        df_trend[column_name + '_formatted'] = df_trend[column_name].map('{:,.0f}'.format)
    
    logger.debug('===========================df_trend=====================')
    logger.debug(df_trend)

    return df_trend.reset_index().to_dict(orient='records')


def fin_indicator_calculation_result(df_fin_indicator_calculation: pd.DataFrame, df_dim_quantative_index: pd.DataFrame) -> pd.DataFrame:
    # (source: calculated from model) df_fin_indicator_calculation(year_data) -> index: year, column: fin_indicator_name_en

    # unpivot all financial indicator.
    unpivot_columns = list(df_fin_indicator_calculation.columns).remove('year') 
    df_unpivot = pd.melt(df_fin_indicator_calculation, id_vars='year', value_vars=unpivot_columns, var_name='fin_indicator_text_en')
    
    # get finaical indicator info from dim table.
    df_unpivot = df_unpivot.merge(df_dim_quantative_index, on='fin_indicator_text_en')

    # df_fin_performance:
    #   only keep main financial indicators.
    df_fin_performance = df_unpivot[df_unpivot.fin_indicator_purpose == 'module-main']
    
    # df_fin_sensitivity:
    # 1. only keep sensitivity calculation result.
    # 2. only base year's value is needed.
    mask = ((df_unpivot.fin_indicator_purpose == 'sensitivity') & (df_unpivot.sensitive_variable_proportion.notnull()))
    df_fin_sensitivity = df_unpivot[mask]
    base_year = df_fin_sensitivity['year'].max()
    df_fin_sensitivity = df_fin_sensitivity[df_fin_sensitivity.year == base_year]
    
    return df_fin_performance, df_fin_sensitivity

def fin_indicator_plot_data(df_fin_performance: pd.DataFrame) -> list:
    chart_data_list = []
    
    # create the list of dict to contain 8 diiferent df with ['df_name_ch','categories', 'series', 'chart_type']
    for indicator_name, df in df_fin_performance.groupby('fin_indicator_text_en'):
        keys = ['df_name_ch','categories', 'series']
        temp_dict =  {key: {} for key in keys}
        temp_dict["df_name_ch"] = list( df['fin_indicator_text_ch'] )[0]
        temp_dict['df_name_ch'] = FIN_INDICATOR_RENAME[ temp_dict['df_name_ch'] ]
        temp_dict["categories"] = list( df["year"] ) 
        temp_dict["series"] = tuple( df["value"] )
        chart_data_list.append(temp_dict)
    
    #reorder the list
    return sorted(chart_data_list, key=lambda x: FIN_INDICATOR_INDEX[x['df_name_ch']]) 
    
def competitor_data_to_ch(df_fin_performance: pd.DataFrame, competitor_data: pd.DataFrame) -> pd.DataFrame | list:
    # reorder the customer's company to the 1st row
    order = ["客戶", "競爭者1", "競爭者2", "競爭者3", "競爭者4"]
    competitor_data = competitor_data.reindex(order)
    competitor_name = list(competitor_data['competitor_name'])
    competitor_data.drop('competitor_name', axis=1, inplace=True)
    
    # group DataFrame by 'fin_indicator_text_en' column and fin_indicator_text_ch for each group
    fin_indicator_text_ch: list = list(df_fin_performance['fin_indicator_text_ch'].unique())
    fin_indicator_text_en: list = list(df_fin_performance['fin_indicator_text_en'].unique())
    
    # convert grouped DataFrame to dictionary
    Table_fin_indicator = dict(zip(fin_indicator_text_en, fin_indicator_text_ch))
    # convert english colname to chinese
    competitor_data = competitor_data.rename(columns=Table_fin_indicator)
    
    return competitor_data, competitor_name 

def fin_competitor_plot_data(competitor_data: pd.DataFrame, competitor_name: list) -> list:
    chart_data_list = []
    
    # create the list of dict to contain 8 diiferent df with ['df_name_ch','categories', 'series', 'chart_type']
    for col in competitor_data.columns:
        keys = ['df_name_ch','categories', 'series']
        temp_dict =  {key: {} for key in keys}
        temp_dict["df_name_ch"] = col
        temp_dict['df_name_ch'] = FIN_INDICATOR_RENAME[ temp_dict['df_name_ch'] ]
        temp_dict["categories"] = competitor_name
        temp_dict["series"] = tuple( competitor_data[col] )
        chart_data_list.append(temp_dict)
    
    #reorder the list
    return sorted(chart_data_list, key=lambda x: FIN_INDICATOR_INDEX[x['df_name_ch']]) 

def top_5_module_by_interviewee(df_qualitative_result_question: pd.DataFrame, df_interviewee: pd.DataFrame, aspect: str) -> pd.DataFrame | dict:
    # choose top 5 modules
    top_5_modules = df_qualitative_result_question[df_qualitative_result_question['aspect'] == aspect].reset_index(drop=True)
    top_5_modules = top_5_modules.groupby(['module']).mean(numeric_only=True).reset_index()
    top_5_modules = list(top_5_modules.nlargest(5, ['gap', 'ql_score']).astype(str)["module"])
    
    print(top_5_modules)
    
    # filter aspect
    df_interviewee = df_interviewee[df_interviewee['aspect'] == aspect].reset_index(drop=True)
    df_interviewee.drop('attribute', axis=1, inplace=True)
    # calculate the gap and choose top t5
    df_temp = df_interviewee['value']
    # subtract even rows from odd rows to receive gap and group module
    df_temp = df_temp[1::2].reset_index(drop=True) - df_temp.iloc[::2].reset_index(drop=True)
    df_interviewee = df_interviewee.iloc[::2].reset_index(drop=True)
    df_interviewee['gap'] = df_temp
    df_interviewee.drop('value', axis=1, inplace=True)
    
    # choose the question which is top 3 of each module
    module_questions = df_interviewee.groupby('module').apply(lambda x: x.nlargest(3, 'gap')).reset_index(drop=True)[['module', 'question']]
    module_questions = module_questions.groupby('module')['question'].apply(lambda x: '\n'.join(set(x))).reset_index()
    # module_questions = df_interviewee.groupby('module')['question'].apply(lambda x: '\n'.join(set(x))).reset_index()
    # calculate the mean group by module and weight_key
    df_interviewee: pd.DataFrame = df_interviewee.groupby(['module',"weight_key"]).mean(numeric_only=True).reset_index()
    # apply function to each group and save result in new column "diff"
    # define aggregation function to calculate max minus min
    aggs = {
        'gap': lambda x: x.max() - x.min()
    }
    # group by "module", and apply aggregation functions
    grouped_diff = df_interviewee.groupby(['module']).agg(aggs).reset_index()
    # rename column to "diff"
    grouped_diff = grouped_diff.rename(columns={'gap': 'diff'})
    grouped_diff['diff'] = round( grouped_diff['diff'] , 2)
    df_interviewee['gap'] = round( df_interviewee['gap'] , 2)
    # joining question
    df_interviewee: pd.DataFrame = pd.merge(df_interviewee, module_questions, on=['module'], how='left')
    df_interviewee: pd.DataFrame = pd.merge(df_interviewee, grouped_diff, on=['module'], how='left')
    
    # mapping the top 5 modules
    df_interviewee = df_interviewee[df_interviewee['module'].isin(top_5_modules)]
    
    # extract the question and diff for text fill
    df_text_diff = df_interviewee[["question","diff"]]
    df_text_diff = df_text_diff.drop_duplicates()
    df_text_diff = df_text_diff.reset_index().to_dict(orient='index') 
    
    print(df_interviewee)

    return df_interviewee , df_text_diff 
