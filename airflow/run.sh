#!/bin/sh


set -o errexit
set -o nounset

airflow db init

airflow users create \
          --username admin \
          --firstname admin \
          --lastname admin \
          --password admin \
          --role Admin \
          --email email@email.com
echo "Starting airflow server"
airflow webserver -p 8500 & sleep 1 & airflow scheduler
echo "server started"
