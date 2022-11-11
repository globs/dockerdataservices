import psycopg2
from psycopg2 import pool
import logging
import common.settings


def singleton(cls):    
    instance = [None]
    def wrapper(*args, **kwargs):
        if instance[0] is None:
            instance[0] = cls(*args, **kwargs)
        return instance[0]

    return wrapper

@singleton    
class DBPooledConnector():

    def __init__(self):
        logging.info("PostgreSQL connection pool initialized")
        #TODO put params in settings/env file
        logging.info( common.settings.getdbcred('pg'))
        self.pg_pool = psycopg2.pool.ThreadedConnectionPool(5, 50, 
                                    user = common.settings.getdbcred('pg')['creds']['pg_user'],
                                    password = common.settings.getdbcred('pg')['creds']['pg_password'],
                                    host = common.settings.getdbcred('pg')['creds']['pg_host'],
                                    port = common.settings.getdbcred('pg')['creds']['pg_port'],
                                    database = common.settings.getdbcred('pg')['creds']['pg_app_db'])
        self.pg_pool.autocommit=True

