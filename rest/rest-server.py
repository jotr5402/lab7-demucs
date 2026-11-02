import hashlib
import io
import json
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, request, Response, send_file
import jsonpickle
import redis

REDIS_WORKER_QUEUE = "toWorker"
redis_client = redis.StrictRedis(
  host = os.getenv("REDIS_HOST", "localhost"),
  port = int(os.getenv("REDIS_SERVICE_PORT", 6379)),
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

existing = {item["Name"] for item in rustfs_client.list_buckets().get("Buckets", [])}
for bucket in [rustfs_queue, rustfs_track]:
  if rustfs_queue not in existing:
    print(f"Creating bucket: {bucket}")
    rustfs_client.create_bucket(Bucket = bucket)


app = Flask(__name__)

@app.post("/")
def webhook_callback():
  print(request.json)
  redis_client.lpush("logging", json.dumps(request.json))

  return Response(status = 200)

@app.post("/apiv1/separate")
def separate():
  body = request.json

  if "mp3" not in body:
    return Response(
      response = f"Body needs to have mp3 field",
      status = 400,
      mimetype = "text/plain"
    )

  try:
    hash = hashlib.md5(str(body["mp3"]).encode("utf-8")).hexdigest()

    print(f"Pushing {hash} to rustfs {rustfs_queue} bucket")
    rustfs_client.put_object(
      Bucket      = rustfs_queue,
      Key         = hash,
      Body        = json.dumps(body),
      ContentType = "application/json"
    )

  except ValueError:
    return Response(
      response = f"mp3 needs to be a string",
      status = 400,
      mimetype = "text/plain"
    )

  except (BotoCoreError, ClientError) as e:
    return Response(
      response = f"Rustfs client failure: {e}",
      status = 500,
      mimetype = "text/plain"
    )

  print(f"Pushing {hash} to worker queue")
  redis_client.lpush(REDIS_WORKER_QUEUE, hash)

  return Response(
    response = jsonpickle.encode({
      "hash": hash,
      "reason": "Song enqueued for separation"
    }),
    status = 200
  )

@app.get("/apiv1/queue")
def queue():
  try:
    queue = redis_client.lrange(REDIS_WORKER_QUEUE, 0, -1)

  except (BotoCoreError, ClientError) as e:
    return Response(
      response = f"Rustfs client failure: {e}",
      status = 500,
      mimetype = "text/plain"
    )

  response = jsonpickle.encode({
    "queue": [q if isinstance(q, str) else q.decode("utf-8") for q in queue]
  })

  return Response(
    response = response,
    status = 200,
    mimetype = "application/json"
  )

TRACKS_ALLOWED = {"base.mp3", "vocals.mp3", "drums.mp3", "other.mp3"}
@app.get("/apiv1/track/<track>")
def track_add(track = None):
  if track is None or track not in TRACKS_ALLOWED:
    return Response(
      response = "Invalid track",
      status = 400,
      mimetype = "text/plain"
    )

  file = io.BytesIO()

  try:
    rustfs_client.download_fileobj(
      Bucket  = rustfs_track,
      Key     = track,
      Fileobj = file
    )

  except (BotoCoreError, ClientError) as e:
    return Response(
      response = f"Rustfs client failure: {e}",
      status = 500,
      mimetype = "text/plain"
    )

  return send_file(
    file,
    download_name = track,
    mimetype = "audo/mpeg"
  )

@app.route("/apiv1/remove/<track>", methods = ["GET", "DELETE"])
def track_remove(track = None):
  if track is None or track not in TRACKS_ALLOWED:
    return Response(
      response = "Invalid track",
      status = 400,
      mimetype = "text/plain"
    )

  try:
    rustfs_client.delete_object(
      Bucket  = rustfs_track,
      Key     = track,
    )

  except (BotoCoreError, ClientError) as e:
    return Response(
      response = f"Rustfs client failure: {e}",
      status = 500,
      mimetype = "text/plain"
    )

  return Response(status = 200)

if __name__ == "__main__":
  app.run(host = "0.0.0.0", port = 5000)
