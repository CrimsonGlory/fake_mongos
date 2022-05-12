FROM python:3
RUN apt-get update && apt-get install -y vim && pip install pymongo==3.12 gevent bottle
COPY . /myapp
