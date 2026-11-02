FROM xserrat/facebook-demucs:latest

WORKDIR /worker

COPY ./worker-server.py ./worker-server.py

RUN pip install --no-cache-dir boto3 redis requests
RUN mkdir input output

ENTRYPOINT ["python3", "/worker/worker-server.py"]
