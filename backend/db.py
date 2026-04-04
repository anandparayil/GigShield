import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "gigshield_db"),
}

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="gigshield_pool",
            pool_size=5,
            **DB_CONFIG,
        )
    return _pool

def get_connection():
    return get_pool().get_connection()
