SHELL := bash
HUB ?= cyzhang

IMAGE ?= discord_quote_bot

.PHONY: build push pull deploy test

build: Dockerfile
	docker build -t $(HUB)/$(IMAGE):$(VERSION) -f Dockerfile .

push:
	docker push $(HUB)/$(IMAGE)::$(VERSION)

pull:
	docker pull $(HUB)/$(IMAGE)::$(VERSION)

deploy:
	docker run --restart unless-stopped -d \
	-e DISCORD_QUOTEBOT_TOKEN=$(DISCORD_QUOTEBOT_DEV_TOKEN) \
	$(HUB)/$(IMAGE)::$(VERSION)

test:
	@echo $(VERSION)