FROM python:3
RUN pip install pymongo==3.12
COPY . /myapp
