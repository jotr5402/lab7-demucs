import base64
import glob
import json
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import redis
import requests
from requests.exceptions import RequestException


REDIS_WORKER_QUEUE = "toWorker"
redis_client = redis.StrictRedis(
  host = os.getenv("REDIS_HOST", "localhost"),
  port = int(os.getenv("REDIS_SERVICE_PORT", 6379)),
  socket_timeout = None
)
 

rustfs_client = boto3.client(
  "s3",
  endpoint_url          = os.getenv("RUSTFS_ENDPOINT", "http://localhost:9000"),
  aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID", "rustfs-lab-user"),
  aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "replace-this-demo-secret"),
  region_name           = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
)

rustfs_queue = os.getenv("RUSTFS_QUEUE", "queue")
rustfs_track = os.getenv("RUSTFS_TRACK", "track")


try:
  while True:
    print("Waiting for song request")
    response = redis_client.brpop(REDIS_WORKER_QUEUE)

    match response:
      case (_, str(h)):
        hash = h
      case (_, bytes(h)):
        hash = h.decode("utf-8")
      case None:
        continue

    print(f"Processing {hash}")
    redis_client.lpush("logging", f"Processing {hash}")


    try:
      request = rustfs_client.get_object(
        Bucket = rustfs_queue,
        Key    = hash
      )
      print("Retrieved request")
      request_json = json.loads( request["Body"].read().decode("utf-8") )

      print("Writing file")
      with open(f"input/{hash}.mp3", "wb") as f:
        f.write(base64.b64decode(request_json["mp3"]))

    except (KeyError, OSError, BotoCoreError, ClientError) as e:
      print(f"Demucs {hash} failed: {e}")
      redis_client.lpush("logging", f"Demucs {hash} failed: {e}")
      continue


    cmd = (
      "python3 -m demucs --out ./output --mp3"
     f"{' -n ' + request_json['model'] if 'model' in request_json else ''}"
     f" ./input/{hash}.mp3"
    ) 

    print("Running demucs")
    exit_code = os.system(cmd)

    if exit_code:
      print(f"Demucs run failed with exit code {exit_code}")
      redis_client.lpush("logging", f"Demucs run failed with exit code {exit_code}")
      continue


    try:
      print("Uploading files")
      for track in glob.glob(f"output/**/{hash}/*.mp3", recursive = True):
        rustfs_client.upload_file(
          Filename = track,
          Bucket   = rustfs_track,
          Key      = f"{hash}-{os.path.basename(track)}"
        ) 

    except (BotoCoreError, ClientError) as e:
      print(f"Demucs {hash} failed: {e}")
      redis_client.lpush("logging", f"Demucs {hash} failed: {e}")


    if "callback" in request_json:
      callback = request_json["callback"]

      try:
        response = requests.post(
          callback["url"],
          data = json.dumps(callback["data"]),
          headers = {"Content-Type": "application/json"}
        )

        print(response)

      except (KeyError, TypeError, ValueError, RecursionError, RequestException) as e:
        print(f"Callback {hash} failed: {e}")
        redis_client.lpush("logging", f"Callback {hash} failed: {e}")

except KeyboardInterrupt:
  sys.exit(0)
