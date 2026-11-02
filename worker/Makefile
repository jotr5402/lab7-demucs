IMAGE ?= lab7-worker:latest
REPO = jotr5402/jotr5402:lab7-worker

.PHONY: build push

build:
	docker build -t $(IMAGE) .
	docker tag $(IMAGE) $(REPO)

push:
	docker push $(REPO)

deploy:
	kubectl apply -f worker-deployment.yaml

deploy-stop:
	kubectl delete deployment worker
