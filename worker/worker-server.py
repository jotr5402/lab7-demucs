import base64
import glob
import json
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import redis


REDIS_WORKER_QUEUE = "toWorker"
redis_client = redis.StrictRedis(
  host = os.getenv("REDIS_HOST", "localhost"),
  port = int(os.getenv("REDIS_PORT", 6379)),
)
 

rustfs_client = boto3.client(
  "s3",
  endpoint_url          = os.getenv("RUSTFS_ENDPOINT", "http://localhost:9000"),
  aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID", "rustfs-lab-user"),
  aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "replace-this-demo-secret"),
  region_name           = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
)

rustfs_queue = os.getenv("RUSTFS_QUEUE", "queue")
rustfs_track = os.getenv("RUSTFS_QUEUE", "track")


try:
  while True:
    try:
      hash = redis_client.brpop(REDIS_WORKER_QUEUE)

      request = rustfs_client.get_object(
        Bucket = rustfs_queue,
        Key    = hash
      )
      request_json = json.loads( request["Body"].read().decode("utf-8") )

      with open(f"input/{hash}.mp3", "wb") as f:
        f.write(base64.b64decode(request_json["mp3"]))

      cmd = f"make run track={hash}"
      if "model" in request_json:
        cmd += f" model={request_json['model']}"

      exit_code = os.system(cmd)

      if exit_code:
        redis_client.lpush("logging", f"Demucs run failed with exit code {exit_code}")
        continue

      for track in glob.glob(f"output/**/{hash}/*.mp3", recursive = True):
        rustfs_client.upload_file(
          Filename = track,
          Bucket   = rustfs_track,
          Key      = f"{hash}-{os.path.basename(track)}"
        ) 
        
    except (KeyError, BotoCoreError, ClientError) as e:
      redis_client.lpush("logging", f"Demucs {hash} failed: {e}")

except KeyboardInterrupt:
  sys.exit(0)
