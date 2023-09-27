# timestamp generation, monitor calculate time.
from datetime import datetime, timezone, timedelta
import time

TIME_ZONE = timezone(timedelta(hours=+8))

# logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

LOG_TIME = datetime.now(TIME_ZONE).strftime('%Y%m%d-%H%M%S')
file_handler = logging.FileHandler(f'LOG\\log-{LOG_TIME}.txt')
logging.getLogger().addHandler(file_handler)

# Type decoration
from io import BytesIO

# parameter read.
import json
def load_config(f_name: str):
    with open(f_name, mode='r', encoding='utf-8') as f:
        config = json.load(f)
    return config
# ----------------------------------------------------------------------------------------------------------------------------
# database
from db.repository_stg import connect, get_user

# module and reporting service
from module.model import apply_model
from reporting.report import generate_report
import ETL

# web server.
import flask
from flask_api import status
from ipaddress import ip_network, ip_address
from hashlib import sha256
# ----------------------------------------------------------------------------------------------------------------------------
# api config
dev_mode = True
app = flask.Flask(__name__)

# api authentication
ALLOWED_IP = load_config('allow_ip.json')
VALID_TOKENS = ('pwcgpscrpt985')

# variables
FIN_DATA_KEY = 'FIN. 請按照填報模板，上傳貴公司的財務資料。'

# change database environment.
DB_INFO = load_config('db\\connection_info.json')['admin']
DB_CONNECTION, DB_META = connect(DB_INFO['host'], DB_INFO['database'], DB_INFO['port'], DB_INFO['user'], DB_INFO['password'])


def authenticate_user(user_email: str, password: str):

    try:
        user: dict = get_user(DB_CONNECTION, user_email)[0]

    except IndexError as e:
        logging.error(f'401: Invalid account - {user_email}')
        flask.abort(401, f'Invalid account - {user_email}')
    
    # compare hash
    hashed_password = sha256(bytes.fromhex(user['salt']) + password.encode()).hexdigest()
    if user['password'] != hashed_password:
        logging.error(f'401: Invalid password for {user_email}')
        flask.abort(401, f'Invalid password for {user_email}')

    logging.info(f'Login Successful: {user_email}')


@app.before_request
def authentication():
    timestamp = datetime.now(TIME_ZONE).isoformat()
    logging.info('========REQUEST START========')
    logging.info(f'start time: {timestamp}')

    # log ip
    if not dev_mode:
        client_ip = str(flask.request.headers['X-Real-IP'])
        client_uri = str(flask.request.headers['X-Request-URI'])
        logging.info(f'from_ip: {client_ip}, request_resource: {client_uri}')
    
    # login
    user_email = flask.request.json.get('user_email')
    password = flask.request.json.get('password')
    authenticate_user(user_email, password)


@app.route('/api/login', methods=['POST'])
def excel_client_login():
    user_email = flask.request.json.get('user_email')
    password = flask.request.json.get('password')    
    authenticate_user(user_email, password)

    return 'OK', 200


@app.route('/api/task', methods=['POST'])
def task():

    logging.info('========TASK START========')
    
    # accept only application/json
    try:
        content: dict = flask.request.get_json()
    except:
        logging.error('400: unsupported content type.')
        flask.abort(400, 'unsupported content type.')

    # check start time
    timestamp = datetime.now(TIME_ZONE).isoformat()
    logging.info(f'start time: {timestamp}')

    # 資料讀取與備份
    input_tables: dict = ETL.extract_tables(content)
    ETL.load_raw_data(DB_CONNECTION, input_tables['df_form_data'], input_tables['df_company_data'], input_tables['df_financial_data'])

    # 模型運算
    tic = time.perf_counter()
    logging.info(f'process: model calculation...')
    calculated_tables: dict = apply_model(conn=DB_CONNECTION, input_tables=input_tables)
    
    # 產出報表
    tac = time.perf_counter()
    logging.info(f'process: report generation...')
    ppt_buffer: BytesIO = generate_report(conn=DB_CONNECTION, input_tables=input_tables, calculated_tables=calculated_tables)

    toc = time.perf_counter()
    logging.info(f"process: model calculation complete in {tac - tic:0.4f} seconds.")
    logging.info(F"process: report generation complete in {toc - tac:0.4f} seconds.")
    logging.info('=========TASK END=========')

    return flask.send_file(ppt_buffer, download_name='result.pptx', as_attachment=True)


def print_dict(dit: dict):
    for key, value in dit.items():
        logging.debug(f'{key}: {value}')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=dev_mode, threaded=True)






    """
    try:
        pass
        #df_solution, df_trend, df_year_data, df_qualitative_result = apply_model(raw_json=content, financial_data_xlsx=financial_data_xlsx)
        #tac = time.perf_counter()
        #ppt_buffer: BytesIO = generate_report(df_solution, df_trend, df_year_data, df_qualitative_result)
    
    except ValueError as e:
        error_detail = {
            "timestamp": timestamp,
            "status": 400,
            "error": str(e)
        }
        return error_detail, status.HTTP_400_BAD_REQUEST
    except Exception as e:
        error_detail = {
            "timestamp": timestamp,
            "status": 500,
            "error": str(e)
        }
        return str(e), status.HTTP_500_INTERNAL_SERVER_ERROR
        #return "伺服器錯誤，若問題持續發生，請聯繫管理員。", status.HTTP_500_INTERNAL_SERVER_ERROR 
    """