#!/bin/sh
kubectl apply -f redis/redis-deployment.yaml
kubectl apply -f redis/redis-service.yaml

./rustfs/install-rustfs.sh

kubectl apply -f rest/rest-deployment.yaml
kubectl apply -f rest/rest-service.yaml
kubectl apply -f rest/rest-ingress.yaml

kubectl apply -f logs/logs-deployment.yaml

kubectl apply -f worker/worker-deployment.yaml

