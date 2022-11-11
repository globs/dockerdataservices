#getting pg env params for postgres exporter settings
pg_env_location='/home/ubuntu/my_projects/git/demodbs/postgresql/adaptme.env'
source $pg_env_location

#create persistant host storage for monitoring services
promotheus_data='/data/promotheus'
sudo mkdir $promotheus_data 
sudo chmod 777 $promotheus_data

sudo mkdir /data/grafana/
sudo chmod 777 /data/grafana/



echo "Recreating internal network"
podman network rm prometheus --force
podman network create prometheus


echo "Creating main pod"
podman pod rm monitoring_services --force
podman pod create --name monitoring_services -p  9091:9090    -p 8000:8000  


echo "Creating exporter containers"
podman rm db2_exporter --force
podman run -d --pod=monitoring_services --name db2_exporter localhost/monitoring_services:LATEST 
# Start an example database
#ced podman run --net=host -it --rm -e POSTGRES_PASSWORD=password postgres
# Connect to it

podman rm postgres_exporter --force
podman run -d \
  --network=prometheus   --pod=monitoring_services --name="postgres_exporter" \
  -e DATA_SOURCE_NAME="postgresql://$PG_USER:$PG_PWD@$PG_HOSTNAME:$PG_PORT/postgres?sslmode=disable" -p 9187:9187 \
  quay.io/prometheuscommunity/postgres-exporter

podman rm promnode --force
podman run -d --network=prometheus --pod=monitoring_services  --name promnode docker.io/prom/node-exporter-linux-amd64

echo" creating prometheus server container"
podman rm promserver --force
podman run -d --network=prometheus --pod=monitoring_services --name promserver -v /home/ubuntu/admin/vps_monitor/appvolume:/etc/prometheus docker.io/prom/prometheus

echo "creating grafana server container"
podman rm grafana --force
podman run -d --network=prometheus  --pod=monitoring_services -p 3000:3000   --name grafana -v /data/grafana:/var/lib/grafana  docker.io/grafana/grafana


