import ast
from dataclasses import dataclass

# https://stackoverflow.com/questions/66919433/how-to-know-ip-of-urlfetchapp-in-google-apps-script
# in this project, we use eval() to calculate financial indicators.
# however, eval() can make the system vulnerable to code injection, if it is used to execute user input argument.

#In order to ensure that eval() can be used safely, following actions are performed:

# financial indicator input (from user upload excel file)
# we make sure that all value in dataframe are converted to numeric type before eval() calculation, otherwise an error would occurred.
# for example -> line 217, in run_quantitative_analysis, df_year_data = df_year_data.apply(pd.to_numeric)

# financial indicator calculation
#1. We only use eval() to calculate financial indicator formulas stored in the database, which are maintained by database administrator.
#2. in case that administrator's db accounts are compromised, We will perform this check to ensure that only numerical operations and logic operations can be executed.

allowed_node: tuple = (
        ast.Expression, ast.operator, ast.Constant,                         # arithmetic calculation
        ast.Compare, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq,   # arithmetic comparison
        ast.BoolOp, ast.And, ast.Or,                                        # logical comparison
        ast.BinOp,                                                          # +, -, *, /, %, // **, <<, >>, &, |, ^
        ast.UnaryOp,                                                        # +, -, ~, not
        ast.Name, ast.Load                                                  # variables parse
        )

@dataclass
class CheckResult:
    isAllowed: bool
    exception: Exception

def formula_check(expr: str) -> CheckResult:

    try:
        expr_tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        return CheckResult(isAllowed=False, exception=e)

    for node in ast.walk(expr_tree):
        if not isinstance(node, allowed_node):
            return CheckResult(isAllowed=False, exception=Exception(f'forbidden method: {type(node)}'))
    
    return CheckResult(isAllowed=True, exception=None)


def test():
    formulas = [
    "CAGR >= (industry_CAGR + 3)",
    "__import__('os').remove('test_remove.txt')",
    "CAGR <= (industry_CAGR - 3)",
    "(ppe_net_value*0.01) * ( 1 + depreciation_expense / ppe_net_value)",
    "__import__('os').listdir('.')",
    "__import__('subprocess').Popen(['tasklist'],stdout=__import__('subprocess').PIPE).communicate()[0]",
    "__import__('code').InteractiveConsole(locals=globals()).interact()",
    "dfk["]
    
    formula_check_result = list(map(lambda formula: formula_check(formula), formulas))
    for check in formula_check_result:
        print(check)
