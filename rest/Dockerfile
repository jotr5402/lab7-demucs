FROM python:3.15-slim

RUN pip install --no-cache-dir boto3 flask jsonpickle redis
COPY ./rest-server.py ./rest-server.py
WORKDIR /
CMD ["python3", "/rest-server.py"]
