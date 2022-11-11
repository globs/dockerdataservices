import os
import time
import yaml
import ibm_db
import ibm_db_dbi
import argparse
from prometheus_client import CollectorRegistry, \
        Gauge, Info, push_to_gateway, start_http_server
from dotenv import load_dotenv
from dotenv import dotenv_values

load_dotenv()
config = dotenv_values(".env")  # config = {"USER": "foo", "EMAIL": "foo@example.org"}
print(config)
push_gateway = os.environ.get('PUSH_GATEWAY')
fix_labels = {
        'keys': ['Database'],
        'values': [os.environ.get('DB2DATABASE')]
        }
job = os.environ.get('JOB')
sql_up = os.environ.get('SQL_UP')
sql_env = os.environ.get('SQL_ENV')
g = {}

db2connectionstring = (
   f"DATABASE={os.environ.get('DB2DATABASE')};"
   f"HOSTNAME={os.environ.get('DB2HOSTNAME')};"
   f"PORT={os.environ.get('DB2PORT')};"
   f"PROTOCOL={os.environ.get('DB2PROTOCOL')};"
   f"UID={os.environ.get('DB2UID')};"
   f"PWD={os.environ.get('DB2PWD')};"
   "ConnectTimeout=6"
)


def gauge_init(registry):
    g_up = Gauge(
            'db2_status',
            'Running a dummy query',
            fix_labels['keys'],
            registry=registry
            )
    g_ts = Gauge(
            'db2_last_check',
            'Last time a check job finished',
            fix_labels['keys'],
            registry=registry,
            )
    return g_up, g_ts


def gauge_list_init(registry, metric, gauge_names, gauge_descrs, label_names):
    g[metric] = []
    for gauge_name, gauge_descr in zip(gauge_names, gauge_descrs):
        g[metric].append(
                Gauge(gauge_name, gauge_descr, label_names, registry=registry)
                )


def check_db_status(registry, g_up, g_ts):
    try:
        conn = ibm_db.connect(db2connectionstring, "", "")
        iconn = ibm_db_dbi.Connection(conn)
        cur = iconn.cursor()
        cur.execute(sql_up)
        g['up'].labels(*fix_labels['values']).set(1)
        g['ts'].labels(*fix_labels['values']).set_to_current_time()
        return iconn

    except Exception as exc:
        g_up.labels(*fix_labels['values']).set(0)
        g_ts.labels(*fix_labels['values']).set_to_current_time()
        print(exc)
        return False


def get_inst_info(iconn, registry):
    cur = iconn.cursor()
    cur.execute(sql_env)
    row = cur.fetchone()
    i = Info(
        'db2_instance',
        'Information aboud the db2 instance',
        registry=registry
        )
    i.info(
            {
                'Instance': row[0],
                'Version': row[1],
                fix_labels['keys'][0]: fix_labels['values'][0]
            }
        )


def get_db_metrics(iconn, metric, sql, label_names):
    cur = iconn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    label_values = []
    label_values.clear()
    for row_ix, row in enumerate(rows):
        label_values.clear()
        label_values.insert(0, *fix_labels['values'])
        for col_ix, col in enumerate(row):
            if col_ix < len(label_names)-1:
                label_values.append(col)
            else:
                g[metric][col_ix-len(label_names)+1].labels(*label_values).set(
                        col if col is not None else 0
                        )


def collect(registry, config_yaml, run_counter):
    if run_counter == 0:
        g['up'], g['ts'] = gauge_init(registry)
    iconn = check_db_status(registry, g['up'], g['ts'])
    if not iconn:
        return registry
    if run_counter == 0:
        get_inst_info(iconn, registry)
    with open(config_yaml, "r") as metrics_file:
        try:
            metrics = yaml.safe_load(metrics_file)
            for metric in metrics:
                if metrics[metric]['labels'] is None:
                    label_names = fix_labels['keys']
                    label_cols = []
                else:
                    labels = [key for key in metrics[metric]['labels']]
                    label_names = [list(label.keys())[0] for label in labels]
                    label_names = fix_labels['keys'] + label_names
                    label_cols = [list(label.values())[0] for label in labels]
                gauges = [key for key in metrics[metric]['gauges']]
                gauge_names = [list(gauge.keys())[0] for gauge in gauges]
                g_pairs = [list(gauge.values())[0] for gauge in gauges]
                gauge_cols = [list(g_pair.keys())[0] for g_pair in g_pairs]
                gauge_descrs = [list(g_pair.values())[0] for g_pair in g_pairs]
                cols = label_cols + gauge_cols
                sql = f"SELECT {', '.join(cols)} "       \
                      f"FROM {metrics[metric]['from']} " \
                      f"WHERE {metrics[metric]['where']}"
                if run_counter == 0:
                    print(f'Initializing {metric}...')
                    gauge_list_init(
                            registry,
                            metric,
                            gauge_names,
                            gauge_descrs,
                            label_names
                            )
                get_db_metrics(iconn, metric, sql, label_names)
        except yaml.YAMLError as exc:
            print(exc)
    return registry


def collect_loop(registry, config_yaml, interval):
    run_counter = 0
    while True:
        collect(registry, config_yaml, run_counter)
        time.sleep(int(interval))
        run_counter += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-c', '--config', dest='config_yaml',
            default='./metrics.yml', help='Configuration YAML file'
            )
    parser.add_argument(
            '-p', '--port', dest='port', type=int,
            default=8000, help="HTTP port to expose metrics"
            )
    parser.add_argument(
            '--push', dest='push_mode',
            default=False, help='If you are using  push gateway'
            )
    args = parser.parse_args()
    registry = CollectorRegistry()
    if args.push_mode is True:
        collect(registry, args.config_yaml, 0)
        push_to_gateway(push_gateway, job=job, registry=registry)
    else:
        start_http_server(args.port, registry=registry)
        collect_loop(
                registry,
                args.config_yaml,
                os.environ.get('COLLECTOR_INTERVAL')
                )


if __name__ == "__main__":
    main()
