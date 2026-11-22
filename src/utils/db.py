import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from pymongo import MongoClient
import redis
import yaml
import os

_config = None
_pg_pool = None
_mongo_client = None
_redis_client = None

def load_config():
    global _config
    if _config is None:
        with open('config/db_config.yaml') as f:
            _config = yaml.safe_load(f)
    return _config

def get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        cfg = load_config()['postgres']
        # Use Docker service name if running in container
        host = os.getenv('POSTGRES_HOST', cfg['host'])
        port = int(os.getenv('POSTGRES_PORT', cfg['port']))
        conn_params = {
            'host': host,
            'port': port,
            'database': cfg['database'],
            'user': cfg['user'],
            'password': cfg['password'],
        }
        _pg_pool = ThreadedConnectionPool(1, cfg.get('pool_size', 5), **conn_params)
    return _pg_pool

def get_pg_conn():
    return get_pg_pool().getconn()

def put_pg_conn(conn):
    get_pg_pool().putconn(conn)

def get_mongo_db():
    global _mongo_client
    if _mongo_client is None:
        cfg = load_config()['mongodb']
        host = os.getenv('MONGO_HOST', cfg['host'])
        port = int(os.getenv('MONGO_PORT', cfg['port']))
        _mongo_client = MongoClient(host, port)
    return _mongo_client[cfg['database']]

def get_redis():
    global _redis_client
    if _redis_client is None:
        cfg = load_config()['redis']
        host = os.getenv('REDIS_HOST', cfg['host'])
        port = int(os.getenv('REDIS_PORT', cfg['port']))
        _redis_client = redis.Redis(host=host, port=port, decode_responses=True)
    return _redis_client
