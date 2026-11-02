IMAGE ?= lab7-rest:latest
REPO = jotr5402/jotr5402:lab7-rest

.PHONY: build push deploy deploy-stop service-stop ingress ingress-stop flask

build:
	docker build -t $(IMAGE) .
	docker tag $(IMAGE) $(REPO)

push:
	docker push $(REPO)

deploy:
	kubectl apply -f rest-deployment.yaml

deploy-stop:
	kubectl delete deployment rest

service:
	kubectl apply -f rest-service.yaml

service-stop:
	kubectl delete service rest

ingress:
	kubectl apply -f rest-ingress.yaml

ingress-stop:
	kubectl delete ingress frontend-ingress

flask:
	python -m flask --app rest-server run
