# discord_quote_bot
A bot that brings the "quote" feature to Discord text chat.

A docker image for this bot is available on Docker Hub: `docker pull cyzhang/discord_quote_bot:latest`.
A docker image for the development version of the bot is available on Docker Hub: `docker pull cyzhang/discord_quote_bot:development`.

# Quickstart

1. Install Docker
2. Pull the image: `docker pull cyzhang/discord_quote_bot`
3. Set your authentication token as `DISCORD_QUOTEBOT_TOKEN` in your environment (e.g., `export DISCORD_QUOTEBOT_TOKEN=[token]`)
4. Run the image: `sudo docker run --restart unless-stopped -d -e DISCORD_QUOTEBOT_TOKEN=$DISCORD_QUOTEBOT_TOKEN cyzhang/discord_quote_bot 
`

# Additional Notes:

- Builds are automated and can be monitored here: [Docker Hub Build Monitoring](https://hub.docker.com/r/cyzhang/discord_quote_bot/builds/)
- Frame data source from https://github.com/D4RKONION/fatsfvframedatajson
