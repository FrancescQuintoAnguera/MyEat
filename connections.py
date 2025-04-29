from pymongo import MongoClient
import pymysql.cursors
from keys import *

sclient = pymysql.connect(host=sql_host, user=sql_user, password=sql_password ,charset="uft8mb4",cursorclass=pymysql.cursors.DictCursor)

mclient = MongoClient(f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:27014/")
