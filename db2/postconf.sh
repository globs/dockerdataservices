ALTER TABLESPACE USERSPACE1 NO FILE SYSTEM CACHING;
ALTER TABLESPACE TEMPSPACE1 NO FILE SYSTEM CACHING;


db2 update db cfg for your_Database_Name using logfilsiz 3000 logprimary 100 logsecond 100
db2set DB2_WORKLOAD=ANALYTICS