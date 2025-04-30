from pymongo import MongoClient
import pymysql
from keys import *

sclient = pymysql.connect(host=sql_host, user=sql_user, database=sql_database, password=sql_password)

mclient = MongoClient(f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:27014/")
