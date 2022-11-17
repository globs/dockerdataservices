import logging
import common.settings
import traceback
import json
from common.db.postgres.dbutils import PostGreSQLUtils
from common.db.db2.dbconnector import DB2Connector
from common.cos.minio.cos_manager import S3COSMinioManager

#todo add parent class to manage variaous non S3 COS if needed or usage of non minio lib

class LoaderConfigManager(object):

    def __init__(self):
        logging.debug('Instanciating LoaderConfigManager')
        self.dbops = PostGreSQLUtils()
        self.db2dbops = DB2Connector()
        self.cosmanager = S3COSMinioManager()
        self.methods = {
            "csvloaders" : {
                "db2":self.transferCSVFileToDB2Table,
                "pg":self.transferCSVFileToPostGRESQLTable
            },
            "dbops" : {
                "db2": self.db2dbops,
                "pg": self.dbops
            }
            
        }

    def __del__(self):
        logging.debug('Destroying LoaderConfigManager')

    def transferCSVFileToPostGRESQLTable(self, bucketname, objectname, pg_schema, pg_table, csv_colsep):
        self.dbops.insertRawCSVToDB(str(self.cosmanager.getObjectData(bucketname, objectname)),
        pg_schema,
        pg_table,
        separator=csv_colsep, 
        columns=None,
        truncate=True)

    def transferCSVFileToDB2Table(self, bucketname, objectname, schema, table, csv_colsep):
        self.db2dbops.insertCSVtoTable(str(self.cosmanager.getObjectData(bucketname, objectname)),schema, table, csv_colsep)



    def apply_json(self, json_string):
        config_dict = json.loads(json_string)
        run_res = []
        for jobconfig in config_dict:
            res_tmp = {
                "jobname" : jobconfig['jobname'],
            }
            logging.info(f"""
            job target db type {jobconfig['dbtype']}
            bucket_name {jobconfig['config']['bucket_name']}
            object_name {jobconfig['config']['object_name']}
            schema {jobconfig['config']['schema']}
            table {jobconfig['config']['table']}
            csv_colsep {jobconfig['config']['csv_colsep']}
            """)
            try:
                if jobconfig['mode'] == 'create':
                    self.methods['dbops'][jobconfig['dbtype']].dropTable(jobconfig['config']['schema'], jobconfig['config']['table'])
                    #self.methods['dbops'][jobconfig['dbtype']].executeQuery(f"DROP TABLE IF EXISTS {jobconfig['config']['schema']}.{jobconfig['config']['table']}")
                    self.methods['dbops'][jobconfig['dbtype']].executeQuery(jobconfig['config']['table_ddl'])
                else: 
                    if jobconfig['mode'] == 'replace':
                        self.methods['dbops'][jobconfig['dbtype']].executeQuery(f"DELETE FROM {jobconfig['config']['schema']}.{jobconfig['config']['table']}")
                for objname in jobconfig['config']['object_name'].split(','):
                    self.methods['csvloaders'][jobconfig['dbtype']](jobconfig['config']['bucket_name'],
                    objname,
                    jobconfig['config']['schema'],
                    jobconfig['config']['table'],
                    jobconfig['config']['csv_colsep'])
            except Exception as e:
                logging.error(f'something went wrong on job')
                res_tmp['error_message'] = f"something went wrong on job {e}"
                res_tmp['job status'] = f'ko'
                run_res.append(res_tmp)
                continue
            res_tmp['job status'] = f'ok'
            run_res.append(res_tmp)
        return run_res
