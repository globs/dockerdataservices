import ibm_db as db
import logging
import common.settings

class DB2Connector():

    def __init__(self):
        logging.info("PostgreSQL connection pool initialized")
        #TODO put params in settings/env file
        logging.info( common.settings.getdbcred('db2'))
        try:
            conn_str = f"DATABASE={common.settings.getdbcred('db2')['creds']['db2_app_db']};HOSTNAME={common.settings.getdbcred('db2')['creds']['db2_host']};PORT={common.settings.getdbcred('db2')['creds']['db2_port']};PROTOCOL=TCPIP;UID={common.settings.getdbcred('db2')['creds']['db2_user']};PWD={common.settings.getdbcred('db2')['creds']['db2_password']};"
            self.conn = db.connect(conn_str, "", "" )
        except Exception as e:
            logging.error('Error while connecting to db2 database')
            logging.error(e)

        
    def __del__(self):
        db.commit(self.conn)
        db.close(self.conn)

    def executeQuery(self, query): 
        try:
            logging.info(f"executing statement: {query}")
            stmt = db.exec_immediate(self.conn, query)
            db.commit(self.conn)
            #print "Number of affected rows: ", ibm_db.num_rows(stmt)
        except Exception as e:
            logging.error('Error while executing query on db2 database')
            logging.error(e)

    def dropTable(self, tabschema, tabname):
        logging.info(f'Dropping table {tabschema}.{tabname}')
        self.executeQuery(f'DROP TABLE {tabschema}.{tabname} IF EXISTS;')

    def insertCSVtoTable(self, csvdata, schema, table, colsep):
        tmpfilename = common.settings.workingdir + "temp_csv.csv"
        f = open(tmpfilename,"w")
        f.write(csvdata)
        f.close()

        sql = f"""
        INSERT INTO {schema}.{table}
        SELECT * FROM EXTERNAL '{tmpfilename}'
        LIKE {schema}.{table}
        USING (
        CCSID 1208  
        STRING_DELIMITER DOUBLE
                DELIMITER '{colsep}' 
                FORMAT TEXT 
                LOGDIR '/home/vincent/temp/'
                REMOTESOURCE 'jdbc'
                )
        ;
        """
        self.executeQuery(sql)

