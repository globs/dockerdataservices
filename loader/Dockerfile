FROM ubuntu:20.04

LABEL author="Vincent GAUTIER" \
      name="Cloud object storage & data utils" \
      version="v1.0-BETA"

#ADD user
RUN useradd -ms /bin/bash dbloader

#Install image dependencies
RUN apt-get -y -qq update \
    && apt-get -y -qq install make gcc g++ libxml2 \
    && apt-get install -y python3.8 python3-pip python3.8-dev\
    build-essential unixodbc-dev libpq-dev curl\
     nano

# Install python project requirements file to container
COPY ["./conf/requirements.txt", \
      "/opt/"]

RUN python3.8 -m pip install --upgrade pip \
    && python3.8 -m pip install -r /opt/requirements.txt \
    && rm /opt/requirements.txt 

RUN mkdir /home/dbloader/project/
COPY src/ /home/dbloader/project/src/
RUN mkdir /home/dbloader/project/logs
RUN chown dbloader:dbloader /home/dbloader/project/logs
WORKDIR /home/dbloader/project/src/

ENV PYTHONPATH="/home/dbloader/project/src/:${PYTHONPATH}"
RUN mkdir /tmp/result_files &&  chown -R dbloader /tmp/result_files
RUN mkdir /home/dbloader/logs &&  chown -R dbloader /home/dbloader/logs
USER dbloader
#CMD ["python3.8", "./main_rest.py"]