__author__ = "Vincent GAUTIER"
__copyright__ = "Copyright 2020, The Bot Project"
__credits__ = ["Vincent GAUTIER", "Jonathan GAUTIER"]
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Vincent GAUTER"
__email__ = "gautier.vincent.ci@gmail.com"
__status__ = "Experimental"
import logging
import common.settings
import traceback
from minio import Minio
import json
from common.db.postgres.dbutils import PostGreSQLUtils
from common.db.db2.dbconnector import DB2Connector


#todo add parent class to manage variaous non S3 COS if needed or usage of non minio lib

class S3COSMinioManager(object):

    def __init__(self):
        logging.debug('Instanciating S3COSManager')
        self.nb_api_calls = 0
        self.credentials = common.settings.minio_creds
        #self.process_pool = ThreadPoolExecutor(10)
        self.buckets = []
        self.dbops = PostGreSQLUtils()
        self.db2dbops = DB2Connector()
        self.connect()

    def __del__(self):
        logging.debug('Destroying S3COSManager')

    def connect(self):
        # Create client with access and secret key.
        self.client = Minio(self.credentials['url'],
        self.credentials['accessKey'],
        self.credentials['secretKey'],
        secure=False)
        buckets = self.client.list_buckets()
        for bucket in buckets:
            print(bucket.name, bucket.creation_date)
    

    def list_objects(self, bucketname):
        # List objects information recursively.
        objects =  self.client.list_objects(bucketname, recursive=True)
        for obj in objects:
            print(str(obj))

    def getObjectData(self, bucket, objectname):
        # Get data of an object.
        string = None
        response = None
        try:
            response = self.client.get_object(bucket, objectname)
            string = response.read().decode('utf-8')
            #logging.debug(string)
            # Read data from response.
        finally:
            if response is None:
                logging.error(f'No file found for bucket:{bucket} objectname:{objectname}')
            else:
                response.close()
                response.release_conn()
            return string


    def transferCSVFileToPostGRESQLTable(self, bucketname, objectname, pg_schema, pg_table, csv_colsep):
        self.dbops.insertRawCSVToDB(str(self.getObjectData(bucketname, objectname)),
        pg_schema,
        pg_table,
        separator='|', 
        columns=None,
        truncate=True)

    def transferCSVFileToDB2Table(self, bucketname, objectname, schema, table, csv_colsep):
        self.db2dbops.insertCSVtoTable(str(self.getObjectData(bucketname, objectname)),schema, table, csv_colsep)



def main():
    try:
        common.settings.init_logging()
        minio_cos = S3COSMinioManager()
        config_manager = LoaderConfigManager()
        config_manager.apply_json(common.settings.db_transfers)
       # minio_cos.transferCSVFileToPostGRESQLTable('main', 'csv/customer.tbl.1', 'public','customer','|')
      #  minio_cos.transferCSVFileToPostGRESQLTable('main', 'csv/lineitem.tbl.1', 'public','lineitem','|')
       # minio_cos.transferCSVFileToDB2Table('main', 'csv/GARANTIES_202210281412.csv', 'ASSURANCE_CIE','GARANTIES',',')
        #minio_cos.list_objects('main')
    except:
        logging.error(traceback.format_exc())
	#binance_loader = backend.binance_api_manager.Binance_api_loader()
	#binance_loader.get_orderbook('LTCBTC')
	#backend.load_influx_from_rest.get_telegram_message_for_markets('BTC','USD')
	#pg_loader.rest_get_market_tickers('binance', '*')
	#pg_loader.rest_get_market_tickers('binance', 'bitcoin')
	#pg_loader.rest_get_all_markets_tickers('bitcoin,ethereum,chainlink,ripple,cardano,tezos,monero,litecoin')
	


#if __name__ == '__main__':
#    main()
