sudo apt install python3.10-venv

#cd db2_exporter
python3 -m venv .
pip3 install -r requirements.txt


echo "
DB2DATABASE = 'testdb'
DB2HOSTNAME = '51.91.11.174'
DB2PORT = '50000'
DB2PROTOCOL = 'TCPIP'
DB2UID = 'db2inst1'
DB2PWD = 'ChangeMe'
PUSH_GATEWAY = "'"'"http://push_gw_host:9091"'"'"
JOB = "'"'"some_job"'"'"
COLLECTOR_INTERVAL = 30
SQL_UP = "'"'"select * from sysibm.sysdummy1"'"'"
SQL_ENV ="'"'"select INST_NAME, SERVICE_LEVEL from SYSIBMADM.ENV_INST_INFO"'"'"
" > ./.env


python3 db2_exporter/db2_exporter.py -p 8000 -c example_config/metrics.yml