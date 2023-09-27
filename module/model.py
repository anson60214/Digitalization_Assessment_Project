# data manipulation
import sqlalchemy as database
import pandas as pd

# model
from module.formula_check import formula_check, CheckResult
import module.data_transformation as transform

# db model
from db.model_stg import *
import db.repository_stg as repo

import logging
logger = logging.getLogger(__name__)

# 常數
STRATEGY_FUNCTION_MAP = {
    "新科技": "aspect_tech",
    "顧客體驗": "aspect_ux",
    "數位營運": "aspect_mfg" ,
    "數位人才": "aspect_ppl"
}

SF_RELATION_IMPACT_WEIGHT_MAP = {
    0: 0,
    1: 1,
    2: 1,
    3: 1
}

#○◎●

SF_RELATION_IMPACT_ICON_MAP = {
    0: '□',
    1: '⊡',
    2: '☑',
    3: '■'
}


STRAT_DICT_KEY = 'STRAT.'

def check_formula(name: str, formula: str):
    result = formula_check(formula)
    if not result.isAllowed:
        raise Exception(f'{str(result.exception)} at {name}')


def calculate_CAGR(dim_fin_indicator: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    # init
    year_count: int = len(df.index)
    y_end, y_start = df.iloc[-1], df.iloc[0]
    
    # CAGR = (Y_end / Y_start) ** (1 / row_count) - 1
    series_CAGR = (
        y_end.divide(y_start).abs()                             # abs(Y_end / Y_start)
        .pow( pd.Series((1 / year_count), index=y_end.index) )  # abs(Y_end / Y_start) ** (1/3)
        .subtract( pd.Series(1, index=y_end.index) )            # subtract by 1
        .multiply( pd.Series(100, index=y_end.index) )          # convert to percentage
        .rename("CAGR")
    )

    # filter indicators required for model.
    df_CAGR = dim_fin_indicator.merge(series_CAGR, left_on="fin_indicator_text_en", right_index=True, how="left")
    df_CAGR = df_CAGR[df_CAGR.fin_indicator_purpose == "module-main"] 

    return df_CAGR


def calculate_trend(dim_financial_trend_index: pd.DataFrame, df_CAGR: pd.DataFrame) -> pd.DataFrame:
    
    df_calculate = dim_financial_trend_index.merge(df_CAGR, on="fin_indicator_id", how="left")

    df_calculate['industry_CAGR'] = 0 # for now(2022/12/13), we assume there is no difference between industry.
    df_calculate['result'] = False # init column
    variables = {'CAGR': 0, 'industry_CAGR': 0} # init variables

    for index, row in df_calculate.iterrows():
        variables['CAGR'], variables['industry_CAGR'] = float(row['CAGR']), float(row['industry_CAGR']) # retrieve variables from dataframe.
        check_formula(row['fin_indicator_id'] + " trend", row['trend_formula'])                         # prevent code injection.
        row['result'] = eval(row['trend_formula'], variables)                                           # calculate string formula, return True or False.
        df_calculate.iloc[index] = row                                                                  # we assign this copy of row back to original dataframe.
    
    df_calculate = df_calculate[df_calculate['result'] == True] # only keep match condition.
    
    return df_calculate[['fin_indicator_id', 'fin_indicator_text_en', 'fin_indicator_text_ch', 'CAGR', 'industry_CAGR', 'trend_name', 'trend_score']]


def calculate_performance_gap_impact_cashflow(df_year_data: pd.DataFrame, sensitivity_performance_select_methods: dict):
    # data cleansing
    # 目標:
    # 1. 將 year data 解開變回 1-dimensional table
    # 2. 整理 產業指標並分出成另一個table + 前處理(刪除空白row, 刪除重複row)
    # 3. 將 (1) 財務指標數值 (2)財務指標敏感度數值 分離為兩個欄位
    # 4. 將兩者合併為單一筆資料，只取擁有敏感度分析的資料列

    # 1
    df_test = pd.melt(df_year_data.reset_index(), id_vars='year')
    # 2
    df_test = df_test[df_test["fin_indicator_text_en"].notna()]
    df_test = df_test.reset_index(drop=True)
    
    df_industry_index = df_test[df_test["fin_indicator_text_en"].str.contains("industry", case=False, na=False)].index 
    df_test.iloc[df_industry_index, 0] = "industry"
    
    df_test2 = df_test.iloc[df_industry_index,:]
    df_test2 = df_test2.drop_duplicates(keep='first')
    df_test2['fin_indicator_text_en'] = df_test2.apply(lambda row: str(row['fin_indicator_text_en']).replace('industry_', ''), axis=1)
    logger.debug(df_test2)

    # 3
    df_test.loc[(df_test.fin_indicator_text_en.str.contains('sensitivity')), 'sensitivity_value'] = df_test.value
    df_test.loc[(df_test.fin_indicator_text_en.str.contains('sensitivity')), 'value'] = 0 
    # 3
    df_test['fin_indicator_text'] = df_test.apply(lambda row: str(row['fin_indicator_text_en']).replace('_sensitivity', ''), axis=1)
    df_test.loc[(~df_test.fin_indicator_text_en.str.contains('sensitivity')), 'fin_indicator_text'] = df_test['fin_indicator_text_en']
    # 4
    df_test = df_test.groupby(['year', 'fin_indicator_text'])[['value', 'sensitivity_value']].sum().reset_index()
    df_test = df_test[(df_test['sensitivity_value'] != 0)]
    df_test2.rename(columns={"fin_indicator_text_en": "fin_indicator_text"}, inplace=True)
    df_test = pd.concat([df_test, df_test2])
    #df_test = df_test.append(df_test2)
    
    #df_test.to_csv("C:/Users/annu/Documents/GitHub/digital-assess-evaluation-model/data/test.csv")
    
    base_year = df_test[pd.to_numeric(df_test['year'], errors='coerce').notnull()]
    base_year = max(base_year['year'].drop_duplicates())
        
    # 商業邏輯: 選擇財務指標表現最好的年度作為 target value ##!加入產業做比較
    for fin_indicator_text, options in sensitivity_performance_select_methods.items():
        mask = f"(df_test.fin_indicator_text == '{fin_indicator_text}')"
        select_method = options['sensitivity_performance_select_method']
        expression = f"df_test[{mask}].value.{select_method}"
        df_test.loc[(df_test['fin_indicator_text'] == fin_indicator_text), 'target_value'] = eval(expression)
    
    log_df("敏感度 (1)- 挑選目標年度", df_test)

    # 商業邏輯: 選擇 base year 數值作為 base value
    # 計算 performance_gap
    df_test = df_test[df_test.year == base_year].copy()
    #df_test.loc[:, 'performance_gap'] = df_test.target_value - df_test.value

    # 若該財務指標為百分比，直接計算差距，反之則使用另一公式。
    for fin_indicator_text, options in sensitivity_performance_select_methods.items():
        if options['use_percentage']:
            df_test.loc[(df_test['fin_indicator_text'] == fin_indicator_text), 'performance_gap'] = df_test.target_value - df_test.value
        else:
            df_test.loc[(df_test['fin_indicator_text'] == fin_indicator_text), 'performance_gap'] = (df_test.target_value - df_test.value) / df_test.value
    
    df_test['performance_gap_impact_cashflow'] = df_test.performance_gap.abs() * df_test.sensitivity_value
    
    log_df("敏感度 (2) - 計算趨勢落差與現金流", df_test)

    return df_test


def run_quantitative_analysis(conn: database.engine, df_financial_data: pd.DataFrame) -> pd.DataFrame:

    df_year_data: pd.DataFrame; formulas: dict; sensitivity_performance_select_methods: dict; variables: dict

    # 財務指標主檔, 解決方案對財務指標相依性分數, 財務指標趨勢判定主檔
    dim_fin_indicator: pd.DataFrame = repo.get_dim_quantative_index(conn)
    dim_sf_relation_score: pd.DataFrame = repo.get_dim_sf_relation_score(conn)
    dim_financial_trend_index: pd.DataFrame = repo.get_dim_financial_trend_index(conn)

    df_year_data, formulas, sensitivity_performance_select_methods, variables = transform.quantitative_data_cleansing(df_financial_data, dim_fin_indicator)
    
    # module-pre calculation.
    for name, value in variables.items():
        df_year_data[name] = value # add constant as column.
    
    # module-main calculation
    for indicator, formula in formulas.items():
        logger.debug(f'{indicator}: {formula}')
        df_year_data[indicator] = df_year_data.eval(formula)
    
    # module-post calculation
    #   複合成長率 calculate CAGR
    #   財務指標趨勢分析 CAGR map trend score
    #   財務指標趨勢落差現金流 trend gap impact cashflow
    df_CAGR = calculate_CAGR(dim_fin_indicator, df_year_data)
    df_trend = calculate_trend(dim_financial_trend_index, df_CAGR)
    df_performance_gap_impact_cashflow = calculate_performance_gap_impact_cashflow(df_year_data, sensitivity_performance_select_methods)
    
    df_trend = df_trend.merge(df_performance_gap_impact_cashflow, left_on='fin_indicator_text_en', right_on='fin_indicator_text', how='left')

    # print('財務指標趨勢落差現金流') print(df_performance_gap_impact_cashflow) print('CAGR calculation') print(df_CAGR)
    #df_trend.to_csv('fin-indicator-CAGR-trend-result.csv', header=True, encoding="utf-8", index=False)

    # 計算量化分數
    #   解決方案對財務指標相依性分數 left join 財務指標趨勢分析gap
    #   量化分數 = 量化相依性分數 * 趨勢分數
    #   計算解決方案得分

    df_sf_score = dim_sf_relation_score.merge(df_trend, on='fin_indicator_id', how='left')
    df_sf_score['sf_score'] = df_sf_score.correlation_score * df_sf_score.trend_score
    df_sf_score = df_sf_score.groupby(['solution_id'])['sf_score'].sum()
    
    return df_sf_score.reset_index(), df_year_data, df_trend


def run_qualitative_analysis(conn: database.engine, df_summarized_form_data: pd.DataFrame, df_company_data: pd.DataFrame) -> pd.DataFrame:
    
    # data read
    dim_sq_relation: pd.DataFrame = repo.get_dim_sq_relation(conn)
    dim_question: pd.DataFrame = repo.get_dim_qualitative_question(conn)

    # 讀取策略重點: {"strategy_id": "STRAT-1", "aspect_ux": "0.25", ...}
    strategy_id: str = df_company_data.loc[df_company_data['id']=="STRAT" , "value"].iloc[0].split(".")[0]
    strategy_weight: dict = repo.get_strategy_weight(conn, strategy_id.strip())[0] 
    
    # 讀取題庫 - 質化題目
    #   map english aspect_id with chinese aspect, using dict STRATEGY_FUNCTION_MAP.
    #   map weight with aspect_id, using dict strategy_weight.
    dim_question['aspect_id'] = dim_question['aspect'].map(STRATEGY_FUNCTION_MAP) 
    dim_question['weight'] = dim_question['aspect_id'].map(strategy_weight)
    
    # data cleasing
    #   metadata(aspect_weight) left join raw data(value).
    df_calculate = dim_question.merge(df_summarized_form_data, on='question_id', how='left')
    df_calculate['attribute'] = df_calculate['attribute'].map({"[現況]": "actual", "[目標]": "target"})
    
    logger.debug(df_calculate)
    logger.debug(df_calculate.columns)
    
    # 計算權重分數
        # pivot target & actual as two column.
        # calculate weighted qualitative score, using weight(metadata), target and actual.
    df_calculate.loc[(df_calculate.attribute == 'actual'), 'actual'] = pd.to_numeric(df_calculate.value)
    df_calculate.loc[(df_calculate.attribute == 'target'), 'target'] = pd.to_numeric(df_calculate.value)
    df_calculate = df_calculate.groupby(["question_id", "aspect", "module", "weight"])[['actual', 'target']].sum().reset_index()
    
    logger.debug(df_calculate)

    df_calculate['gap'] = df_calculate.target - df_calculate.actual
    df_calculate['ql_score'] = df_calculate.weight * df_calculate.gap
    
    logger.debug(df_calculate)
    #df_calculate.to_csv('qualitative-question-result.csv', header=True, encoding="utf-8", index=False)

    # 計算質化分數
        # metadata(correlation_score) left join df_calculate(ql_score)
        # 質化分數 = 權重分數 * 相依性分數
        # 計算解決方案得分
    df_sq_score = dim_sq_relation.merge(df_calculate, on='question_id', how='left')
    df_sq_score['sq_score'] = df_sq_score.ql_score * df_sq_score.correlation_score
    logger.debug(df_sq_score)
    df_sq_score = df_sq_score.groupby(['solution_id'])['sq_score'].sum()

    logger.debug(df_sq_score)
    
    return df_sq_score.reset_index(), df_calculate


def calculate_solution_roi(conn: database.engine, df_result: pd.DataFrame, df_trend: pd.DataFrame) -> pd.DataFrame:
    # goal
    # 1. 生成"improved_KPI": 在報告中，每一個 solution 會有自己的 solution description 頁面，說明此 solution 能夠提升的財務指標。
    # 2. 計算 solution ROI.
    df_dim_sf_relation: pd.DataFrame = repo.get_dim_sf_relation_score(conn)
    df_dim_quantative_index: pd.DataFrame = repo.get_dim_quantative_index(conn)
    df_dim_solution: pd.DataFrame = repo.get_dim_solution(conn)
    
    # column: solution_id  correlation_score(sf_score) sf_score fin_indicator_text
    # 1. for each solution-fin_indicator，為 sf_score 對應其 impact_icon.
    # 2. for each solution-fin_indicator，生成"財務指標顯示文字". ex: "■ 固定資產周轉率" 表示該 solution 能有效提升此指標表現。
    # 3. for each solution, 將該 solution 的所有"財務指標顯示文字" concat 成為單一字串。

    # 1.
    df_impact = df_result.merge(df_dim_sf_relation, on='solution_id', how='left')
    df_impact['financial_impact_icon'] = df_impact['correlation_score'].map(SF_RELATION_IMPACT_ICON_MAP)

    # 2. 
    df_impact = df_impact.merge(
        df_dim_quantative_index[['fin_indicator_id', 'fin_indicator_text_en', 'fin_indicator_text_ch', 'fin_indicator_purpose']]
        , on='fin_indicator_id' , how='left')
    
    df_impact['display_text'] = df_impact.financial_impact_icon + " " + df_impact.fin_indicator_text_ch

    # 3.
    for solution_id, df in df_impact.groupby('solution_id'):
        df_impact.loc[(df_impact.solution_id == solution_id), 'result_text'] = '\n'.join(list(df['display_text']))
    
    logger.debug(df_impact.to_string())


    # 1. for each solution-fin_indicator, 為 sf_score 對應其 impact weight, 並 left join df_trend 後計算權重後趨勢落差現金流.
    # 2. group by solution, 加總 weighted performance gap impact cashflow.
    # 3. df_impact left join dim_solution 取得 平均成本價格, 計算 ROI.

    # 1
    df_impact['financial_impact_weight'] = df_impact['correlation_score'].map(SF_RELATION_IMPACT_WEIGHT_MAP)
    df_impact = df_impact.merge(df_trend[['fin_indicator_id', 'performance_gap_impact_cashflow']], on='fin_indicator_id' , how='left')
    df_impact['weighted_performance_gap_impact_cashflow'] = df_impact.financial_impact_weight * df_impact.performance_gap_impact_cashflow

    log_df("ROI 計算 (1)", df_impact.to_string())

    # 2
    df_impact = (df_impact.
                 groupby(['solution_id', 'sq_score', 'sf_score', 'final_score', 'result_text'])[['weighted_performance_gap_impact_cashflow']]
                 .sum().reset_index())
    
    log_df("ROI 計算 (2) - 加總", df_impact.to_string())

    # 3
    df_solution = df_impact.merge(df_dim_solution, on='solution_id', how='left')
    df_solution['ROI'] = ( df_solution.weighted_performance_gap_impact_cashflow * 0.1) / df_solution.average_price

    return df_solution.sort_values('final_score', ascending=False)


def apply_model(conn: database.engine, input_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    
    # 資料前處理
    df_summarized_form_data: pd.DataFrame = transform.summarized_form_data(input_tables['df_form_data'], input_tables['df_form_weight'])
    df_company_data: pd.DataFrame = input_tables['df_company_data']
    df_financial_data: pd.DataFrame = input_tables['df_financial_data']
    df_solution_filter: pd.DataFrame = transform.solution_filter(input_tables['df_solution_filter'])


    # 解決方案推薦
    df_sq_score: pd.DataFrame; df_qualitative_result: pd.DataFrame
    df_sf_score: pd.DataFrame; df_year_data: pd.DataFrame; df_trend: pd.DataFrame
    df_sq_score, df_qualitative_result  = run_qualitative_analysis(conn, df_summarized_form_data, df_company_data)
    df_sf_score, df_year_data, df_trend = run_quantitative_analysis(conn, df_financial_data)


    # 計算綜合分數
    # 根據使用者設定，篩選 solution
    # 取排名前10
    df_result = df_sq_score.merge(df_sf_score, on='solution_id', how='outer').fillna(0)
    df_result['final_score'] = df_result.sq_score + df_result.sf_score
    df_result = df_solution_filter.merge(df_result, on='solution_id', how='left')
    df_result = df_result.nlargest(10, 'final_score')


    # 計算解決方案 ROI
    log_df('解決方案 前10名', df_result)
    df_solution = calculate_solution_roi(conn, df_result, df_trend)
    
    log_df('解決方案 ROI', df_solution[['solution_id', 'final_score', 'weighted_performance_gap_impact_cashflow','average_price' , 'ROI']])
    log_df('財務指標運算', df_year_data.reset_index().to_string())
    log_df('質化指標', df_qualitative_result)
    log_df('趨勢現金流分析', df_trend.to_string())

    # output
    output_tables: dict = {}
    output_tables['解決方案前十名與ROI'] = df_solution
    output_tables['三年財務指標運算結果'] = df_year_data.reset_index()
    output_tables['質化分析運算結果'] = df_qualitative_result
    output_tables['趨勢現金流與敏感度分析'] = df_trend

    return output_tables

def log_df(name: str, df) -> None:
    logger.debug(name)
    logger.debug(df)