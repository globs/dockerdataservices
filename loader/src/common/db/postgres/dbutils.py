import logging
from common.db.postgres.dbconnector import dbconnector
from common.db.postgres.dbpooledconnector import DBPooledConnector
import psycopg2
import pandas as pd
import common.settings
import common.utils
import io
import os
import json
import traceback
import asyncio


class PostGreSQLUtils():

    def __init__(self):
        logging.debug('Instanciating PostGres Utils classs')

    def dropTable(self, tabschema, tabname):
        logging.info(f'Dropping table {tabschema}.{tabname}')
        self.executeQuery(f'DROP TABLE IF EXISTS {tabschema}.{tabname} ;')

    def clean_old_data(self, table_schema, table_name):
        sql = f"""
        delete from {table_schema}.{table_name} a 
        where a.ts < current_timestamp - interval '{common.settings.db_retention_hours} hour'
        """
        self.executeQuery(sql)

    def get_table_cols_str(self, tabname, filteredcols=None, column_prefix=''):
        try:
            cnn = DBPooledConnector().pg_pool.getconn() 
            res = []
            if filteredcols:
                additional_filter = f" AND column_name not in ({filteredcols}) order by ordinal_position"
            else:    
                additional_filter = 'order by ordinal_position'
            sql = f"""
                SELECT string_agg(column_name, ', ')
                FROM (SELECT column_name from  INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{tabname}'
                {additional_filter} ) a
                ;
                """
            cursor = cnn.cursor()
            cursor.execute(sql)
            columns = cursor.fetchall()
            for column in columns:
                res = column[0]
        except Exception as e:
            logging.error(f'Observer notification error: {e}')
        finally:
            DBPooledConnector().pg_pool.putconn(cnn)   
        return res

    def get_table_cols_list(self, tabname, filteredcols=None):
        try:
            cnn = DBPooledConnector().pg_pool.getconn() 
            res = []
            if filteredcols:
                additional_filter = f" AND column_name not in ({filteredcols}) order by ordinal_position"
            else:    
                additional_filter = 'order by ordinal_position'
            sql = f"SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tabname}' {additional_filter} "
            cursor = cnn.cursor()
            cursor.execute(sql)
            columns = cursor.fetchall()
            for column in columns:
                res.append(column[0])
        except Exception as e:
            logging.error(f'error while getting columns list: {e}')
        finally:
            DBPooledConnector().pg_pool.putconn(cnn)   
        return res

    def get_table_cols_from_json_item(self, json_item):
        columns = list(json_item.keys())
        #res = ', '.join(columns)
        return tuple(columns)

    def get_data_from_json(self, json_item):
        data_items = ()
        for key in json_item:
            data_items = data_items + (str(json_item[key]),)
        return common.settings.csv_separator.join(map(common.utils.clean_csv_value, data_items))


    def clearDbTable(self, schema, table):
        cnn = DBPooledConnector().pg_pool.getconn()
        sql = f"DELETE FROM {schema}.{table}"
        vaccum_sql = f"VACUUM FULL {schema}.{table}"
        logging.debug(sql)
        try:
            cursor = cnn.cursor()    
            cursor.execute(sql)
            #cursor.execute(vaccum_sql)
            cnn.commit()
        except: 
            logging.error(f"Error while clearing table {schema}.{table}")    
            logging.error(traceback.format_exc())    
        finally:
            cursor.close()  
            DBPooledConnector().pg_pool.putconn(cnn)                
      

    def executeQuery(self, sql,  withResults=False):
        cnn = DBPooledConnector().pg_pool.getconn()
        res = []
        logging.info(sql)
        try:
            cursor = cnn.cursor()    
            cursor.execute(sql)
            if withResults:
                rows = cursor.fetchall()
                for row in rows:
                    logging.debug(row)
                    res.append(row)    
            else:
                cnn.commit()
        except: 
            logging.error(traceback.format_exc())    
        finally:
            cursor.close()  
            DBPooledConnector().pg_pool.putconn(cnn)                
        return res        


    def getDFFromSQL(self, sql):
        cnn = DBPooledConnector().pg_pool.getconn()
        res = pd.read_sql_query(sql, cnn)
        DBPooledConnector().pg_pool.putconn(cnn)
        return res

    def getDBOject(self, source_table, filter_values=None, order_values=None):
        logging.debug(f"source table {source_table} filters : {filter_values}")
        cnn = DBPooledConnector().pg_pool.getconn()
        if filter_values:
            sql_where = ' WHERE ' + ' and '.join(filter_values)
        else: 
            sql_where = ""
        if order_values:
            sql_order_by = f"ORDER BY {order_values}"
        else:
            sql_order_by = ""
        columns = self.get_table_cols_list(source_table)
        res = []
        sql = f"SELECT * FROM api_import.{source_table}   {sql_where} {sql_order_by}"
        logging.debug(sql)
        cursor = cnn.cursor(cursor_factory=psycopg2.extras.DictCursor)    
        cursor.execute(sql)
        cnn.commit()
        rows = cursor.fetchall()
        for row in rows:
            logging.debug(row)
            tmp_order = {}
            for key in columns:
                tmp_order[key] = row[key]
            res.append(tmp_order)    
        cursor.close()
        DBPooledConnector().pg_pool.putconn(cnn)
        return res


    def insertDataFrameToDBBulk(self, dataframe, target_table):
        cnn = DBPooledConnector().pg_pool.getconn()
        columns = tuple(dataframe.columns)
        sql_stringio = io.StringIO()
        dataframe.to_csv(sql_stringio, header=False, index=False, sep=common.settings.csv_separator)
        logging.debug(f"target_table={target_table} cols={columns}")
        logging.debug(f"{sql_stringio.getvalue()}")
        cursor = cnn.cursor()
        sql_stringio.seek(0)
        try:
            cursor.execute("SET search_path TO api_import")
            cursor.copy_from(sql_stringio, target_table, sep=common.settings.csv_separator,columns=columns)
            cnn.commit()
        except: 
            logging.error(traceback.format_exc())    
        finally:
            cursor.close()  
            DBPooledConnector().pg_pool.putconn(cnn)


    def insertJsonToDBBulk(self, array_jsondata, target_table):
        cnn = DBPooledConnector().pg_pool.getconn()
        columns = self.get_table_cols_from_json_item(array_jsondata[0])
        data = ''
        for jsondata in array_jsondata:
            data += self.get_data_from_json(jsondata)+ "\n"
        logging.debug(f"target_table={target_table} cols={columns} data= {data}")
        cursor = cnn.cursor()
        sql_stringio = io.StringIO()
        sql_stringio.write(data)      
        sql_stringio.seek(0)
        try:
            cursor.execute("SET search_path TO api_import")
            cursor.copy_from(sql_stringio, target_table, sep=common.settings.csv_separator,columns=columns)
            cnn.commit()
        except: 
            logging.error(traceback.format_exc())    
        finally:
            cursor.close()  
            DBPooledConnector().pg_pool.putconn(cnn)


    def insertJsonToDB(self, jsondata, target_table):
        cnn = DBPooledConnector().pg_pool.getconn()
        columns = self.get_table_cols_from_json_item(jsondata)
        data = self.get_data_from_json(jsondata)
        logging.debug(f" data= {data} cols={columns}")
        cursor = cnn.cursor()
        sql_stringio = io.StringIO()
        sql_stringio.write(data+ "\n")      
        sql_stringio.seek(0)
        #cursor.execute('select * from api_import.tpt_signals')
        cursor.execute("SET search_path TO api_import")
        cursor.copy_from(sql_stringio, target_table, sep=common.settings.csv_separator,columns=columns)
        cursor.close()  
        cnn.commit()
        DBPooledConnector().pg_pool.putconn(cnn)


    def insertRawCSVToDB(self, rawdata, target_schema, target_table, separator=common.settings.csv_separator, columns=None, truncate=False):
        if columns is None:
            columns = self.get_table_cols_list(target_table, "'id','ts'")
        if truncate:
            self.executeQuery(f"delete from {target_schema}.{target_table} a ")
        logging.info(f'columns {columns}')
        logging.debug(f'{rawdata}')
        strIO = io.StringIO()
        strIO.write(rawdata)
        strIO.seek(0)
        self.insertStringIOToDB(strIO, target_schema, target_table, columns)

    def insertStringIOToDB(self, stringio_data, target_schema, target_table, columns, separator=common.settings.csv_separator):
        try:
            cnn = DBPooledConnector().pg_pool.getconn()
            cursor = cnn.cursor()
            cursor.execute(f"SET search_path TO {target_schema}")
            cursor.copy_from(stringio_data, target_table, sep=separator,columns=columns)
        except Exception as e:
            logging.error(f'Bulk insert in pg database error: {e}')
        finally:
            cursor.close()  
            cnn.commit()
            DBPooledConnector().pg_pool.putconn(cnn)


    def subscribeSockets(self, observable):
        observable.subscribe(self)



#Todo add SCD2 type method : input table, primary cdc key, pivot key, target table        

    def generate_md5_formula(self, schema, table, column_prefix=''):
        sql = f"""
        SELECT 'md5(' || string_agg(  'a.' ||colname, ' || ''-'' || ') || ')'
        FROM api_import.tpt_rt_cdc_keys
        WHERE tabname = '{table}'
        and key_type = 'md5cols'
        """
        sql_res = self.executeQuery(sql, withResults=True)
        if len(sql_res) > 0:
            res = sql_res[0][0]
        else:
            logging.error('No md5 key found')
            res = None
        return res

    def generate_cdc_joinkey_str(self, schema, table, source_table_prefix='', target_table_prefix=''):
        sql = f"""
        SELECT string_agg(  '{source_table_prefix}' ||colname || ' = ' || '{target_table_prefix}' || colname , ' and ') 
        FROM api_import.tpt_rt_cdc_keys
        WHERE tabname = '{table}'
        and key_type = 'joinkey'
        """
        sql_res = self.executeQuery(sql, withResults=True)
        if len(sql_res) > 0:
            res = sql_res[0][0]
        else:
            logging.error('No join key found')
            res = None
        return res

    #get only first column of join clause for WHERE IS NULL test
    def generate_cdc_coltest_null(self, schema, table, column_prefix=''):
        sql = f"""
        SELECT  '{column_prefix}' || colname || ' IS NULL '
        FROM api_import.tpt_rt_cdc_keys
        WHERE tabname = '{table}'
        and key_type = 'joinkey'
        limit 1
        """
        sql_res = self.executeQuery(sql, withResults=True)
        if len(sql_res) > 0:
            res = sql_res[0][0]
        else:
            logging.error('No join key found')
            res = None
        return res


    def generate_cdc_keys_str(self, schema, table, key_type, column_prefix=''):
        sql = f"""
        SELECT string_agg(  '{column_prefix}' ||colname, ', ') 
        FROM api_import.tpt_rt_cdc_keys
        WHERE tabname = '{table}'
        and key_type = '{key_type}'
        """
        sql_res = self.executeQuery(sql, withResults=True)
        if len(sql_res) > 0:
            res = sql_res[0][0]
        else:
            logging.error(f'No {key_type} key found')
            res = None
        return res
#create scd0 function
#prendre en compte des formules sur les tables source (creer table param de subsitution)
    def changeDataCapture(self, input_schema, input_table, target_schema, target_table, full_mode=True, checkIntegrity=False, clearSourceTable=False):
        try:
            tabname_newrows_tmp = f"{target_table}_tmp"
            newrows_md5 = self.generate_md5_formula(input_schema, input_table, 'a.')
            newrows_targetcols = self.get_table_cols_str(target_table, "'id','ts'")
            newrows_sourcecols = self.generate_cdc_keys_str(input_schema , input_table, 'source columns', 'a.')
            newrows_valid_from = f"now()"
            newrows_valid_to = f"'9999/12/31'"
            newrows_deleted = f"'9999/12/31'"
            newrows_joinkey = self.generate_cdc_joinkey_str(input_schema, input_table, 'a.', 'b.')
            newrows_all_sourcecols = f"{newrows_sourcecols},{newrows_valid_from},{newrows_valid_to},{newrows_deleted},{newrows_md5},1"
            newrows_col_test_null = self.generate_cdc_coltest_null(input_schema, input_table, 'b.')
            sourcerows_col_test_null = self.generate_cdc_coltest_null(input_schema, input_table, 'a.')
            update_joinkey =  self.generate_cdc_joinkey_str(input_schema, input_table, 'a.', 'filter_query.')
            filter_cols = self.generate_cdc_keys_str( input_schema, input_table, 'joinkey','b.')
            all_queries = []
            sql_insert_new_rows = f"""
                    insert into {target_schema}.{target_table}
                    ({newrows_targetcols})
                    select
                    {newrows_all_sourcecols}
                    from {input_schema}.{input_table} a 
                    left outer join {target_schema}.{target_table} b 
                    on {newrows_joinkey}
                    where {newrows_col_test_null}
            """
            sql_close_changed_rows_old = f"""
                    /*
                    2-2 modified rows (closed all row)
                    */
                    update {target_schema}.{target_table}  a 
                    set valid_to  = now(), line_type=3
                    from  (
                    select 
                    {filter_cols}
                    from {input_schema}.{input_table}  a 
                    inner join {target_schema}.{target_table} b 
                    on {newrows_joinkey}
                    where 
                    b.valid_to  = '9999/12/31' and
                    {newrows_md5}
                    <> 
                    b.comparison_hash 
                    ) as filter_query
                    where 
                    a.valid_to  = '9999/12/31' and 
                    {update_joinkey}
                    ;

            """
            changed_rows_tmp_all_sourcecols = f"{newrows_sourcecols},{newrows_valid_from},{newrows_valid_to},{newrows_deleted},{newrows_md5},2"
            sql_insert_changed_rows_tmp = f"""
                            /*
                    (
                    2-1- modified rows (new opened row)
                    */
                    insert into {target_schema}.{tabname_newrows_tmp}
                    ({newrows_targetcols})
                    select 
                    {changed_rows_tmp_all_sourcecols}
                    from {input_schema}.{input_table} a 
                    inner join {target_schema}.{target_table} b 
                    on {newrows_joinkey}
                    where 
                    b.valid_to  = '9999/12/31' and
                    {newrows_md5}
                    <> 
                    b.comparison_hash 
                    ;
            """
            sql_insert_changed_rows_new = f"""
                    insert into {target_schema}.{target_table} (
                    {newrows_targetcols}
                    )
                    select                
                    {newrows_targetcols}
                    from {target_schema}.{tabname_newrows_tmp}
            """
            sql_delete_rows = f"""
                            /*
                    4- deleted rows
                    */
                    update {target_schema}.{target_table} a 
                    set deleted_from = now(), line_type=4
                    from (
                    select 
                    {filter_cols}
                    from {input_schema}.{input_table} a 
                    right outer join {target_schema}.{target_table} b 
                    on {newrows_joinkey}
                    where {sourcerows_col_test_null} and b.deleted_from = '9999/12/31') as filter_query
                    where a.deleted_from  = '9999/12/31' and 
                    {update_joinkey}
                    ;
            """
            #check source and target unicity (optional)
            all_queries.append(sql_delete_rows)
            all_queries.append(sql_insert_changed_rows_new)
            all_queries.append(sql_insert_changed_rows_tmp)
            all_queries.append(sql_close_changed_rows_old)
            all_queries.append(sql_insert_new_rows)
            for query in all_queries:
                logging.debug(f"Executing query: {query}")
                self.executeQuery(query)
        except Exception as e:
            logging.error(f'Change data capture error: {e}')
            
