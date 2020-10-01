HUB ?= cyzhang
VERSION ?= development

IMAGE ?= discord_quote_bot

.PHONY: build push pull deploy-dev deploy-prod

build: Dockerfile
	docker build -t $(HUB)/$(IMAGE):$(VERSION) -f Dockerfile .

push:
	docker push $(HUB)/$(IMAGE):$(VERSION)

pull:
	docker pull $(HUB)/$(IMAGE):$(VERSION)

deploy-local:
	docker run --restart unless-stopped -d \
	-e DISCORD_QUOTEBOT_TOKEN=$(DISCORD_QUOTEBOT_LOCAL_TOKEN) \
	-e DISCORD_QUOTEBOT_BUCKET=$(DISCORD_QUOTEBOT_DEV_BUCKET) \
	-e DISCORD_QUOTEBOT_DB_FILENAME=$(DISCORD_QUOTEBOT_DB_DEV_FILENAME) \
	-e AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
	-e AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
	-e AWS_DEFAULT_REGION=$(AWS_DEFAULT_REGION) \
	$(HUB)/$(IMAGE):$(VERSION)

deploy-dev:
	docker run --restart unless-stopped -d \
	-e DISCORD_QUOTEBOT_TOKEN=$(DISCORD_QUOTEBOT_DEV_TOKEN) \
	-e DISCORD_QUOTEBOT_BUCKET=$(DISCORD_QUOTEBOT_DEV_BUCKET) \
	-e DISCORD_QUOTEBOT_DB_FILENAME=$(DISCORD_QUOTEBOT_DB_DEV_FILENAME) \
	$(HUB)/$(IMAGE):development

deploy-prod:
	docker run --restart unless-stopped -d \
	-e DISCORD_QUOTEBOT_TOKEN=$(DISCORD_QUOTEBOT_TOKEN) \
	-e DISCORD_QUOTEBOT_BUCKET=$(DISCORD_QUOTEBOT_BUCKET) \
	-e DISCORD_QUOTEBOT_DB_FILENAME=$(DISCORD_QUOTEBOT_DB_FILENAME) \
	$(HUB)/$(IMAGE):latest