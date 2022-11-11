import psycopg2
import logging
import common.settings
from common.db.postgres.dbpooledconnector import DBPooledConnector

def dbconnector(func):
    def with_connection_(*args,**kwargs):
       # pgpool = DBPooledConnector()
       # cnn = pgpool.pg_pool.getconn()
        cnn = psycopg2.connect(user = common.settings.getdbcred('pg')['creds']['pg_user'],
                                  password = common.settings.getdbcred('pg')['creds']['pg_password'],
                                  host = common.settings.getdbcred('pg')['creds']['pg_host'],
                                  port = common.settings.getdbcred('pg')['creds']['pg_port'],
                                  database = common.settings.getdbcred('pg')['creds']['pg_app_db'])                       
        if (DBPooledConnector().pg_pool):
            logging.debug("Pool instance ok")
        else:
            logging.error('Issue with PG connexion pool')
        if (cnn):
            logging.debug("connection ok")
        else:
            logging.error('Connexion creation failed')    
        cnn.autocommit=True
        try:
            rv = func(cnn, *args,**kwargs)
        except Exception as e:
            cnn.rollback()
            logging.error(f'Database connection error: {e}')
            raise
        else:
            logging.debug('query executed successfully')
        finally:
            cnn.commit()
            cnn.close()
        return rv
    return with_connection_