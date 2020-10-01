SHELL := bash
HUB ?= cyzhang

IMAGE ?= discord_quote_bot

.PHONY: build push pull deploy-prod deploy-dev test

build: Dockerfile
	docker build -t $(HUB)/$(IMAGE):$(VERSION) -f Dockerfile .

push:
	docker push $(HUB)/$(IMAGE)::$(VERSION)

pull:
	docker pull $(HUB)/$(IMAGE)::$(VERSION)

deploy-prod:
	docker run --restart unless-stopped -d \
	-e DISCORD_QUOTEBOT_TOKEN=$(DISCORD_QUOTEBOT_TOKEN) \
	$(HUB)/$(IMAGE)::latest

deploy-dev:
	docker run --restart unless-stopped -d \
	-e DISCORD_QUOTEBOT_TOKEN=$(DISCORD_QUOTEBOT_DEV_TOKEN) \
	$(HUB)/$(IMAGE)::development

test:
	@echo $(VERSION)