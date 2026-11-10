import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import logging

class DBCore:
    _pool = None
    
    @classmethod
    def initialize_pool(cls, host="localhost", database="myapp", user="postgres", password="", port=5432, minconn=1, maxconn=10):
        """App start hone par ek baar pool create karta hai."""
        if cls._pool is None:
            try:
                cls._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn, 
                    maxconn, 
                    host=host, 
                    database=database, 
                    user=user, 
                    password=password, 
                    port=port
                )
                logging.info("Database Connection Pool successfully initialized.")
            except Exception as e:
                logging.error(f"Pool initialize karne me error: {e}")
                raise

    @classmethod
    @contextmanager
    def get_connection(cls):
        """Pool se connection deta hai aur automatically return karta hai."""
        if cls._pool is None:
            raise RuntimeError("DatabaseManager initialize nahi hua hai. main.py me pehle initialize_pool call karein.")
        
        conn = cls._pool.getconn()
        try:
            yield conn
            conn.commit()  # Sab sahi raha toh auto commit
        except Exception as e:
            conn.rollback()  # Koi error aayi toh auto rollback
            logging.error(f"Transaction Rollback: {e}")
            raise
        finally:
            cls._pool.putconn(conn)  # Connection pool me wapas submit ho gaya

    @classmethod
    def close_all(cls):
        """App exit hone par pool close karta hai."""
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
            logging.info("Database Connection Pool closed.")
