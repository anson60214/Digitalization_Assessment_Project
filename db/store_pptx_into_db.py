import collections 
import collections.abc
from pptx import Presentation
from io import BytesIO
import json
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import mapper, sessionmaker
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

#load an existing presentation into the pptx variable and read its contents as bytes 
presentation = Presentation(r'C:\Users\annu\Documents\GitHub\digital-assess-evaluation-model\reporting\reporting-template.pptx')
pptx_bytes  = BytesIO()
presentation.save(pptx_bytes)
pptx_bytes.seek(0)
pptx_bytes_data = pptx_bytes.getvalue()
#print(pptx_bytes_data)
 
# Reflect the existing table into a Table object
meta = MetaData(schema='stg')
report_template = Table('dim_report_template', meta, autoload=True, autoload_with=DB_CONNECTION)

# Define a model class that corresponds to the reflected table
class MyModel(object):
    pass

# Map the model class to the reflected table
mapper(MyModel, report_template)

# Create a new instance of the model class
model_instance = MyModel()
model_instance.report_data = pptx_bytes_data

#Add the Powerpoint object to the session and commit the transaction:
Session = sessionmaker(bind=DB_CONNECTION)
session = Session()
session.add(model_instance)
session.commit()
session.close()
