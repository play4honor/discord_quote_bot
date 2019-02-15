# discord_quote_bot
A bot that brings the "quote" feature to Discord text chat.

A docker image for this bot is available on Docker Hub: `docker pull cyzhang/discord_quote_bot`.

# Quickstart

1. Install Docker
2. Pull the image: `docker pull cyzhang/discord_quote_bot`
3. Set your authentication token as `DISCORD_QUOTEBOT_TOKEN` in your environment 

    ```
    export DISCORD_QUOTEBOT_TOKEN=[token]
    ```

4. Run the image: 

    ```
    sudo docker run --restart unless-stopped \
    -d -e DISCORD_QUOTEBOT_TOKEN=$DISCORD_QUOTEBOT_TOKEN \
    cyzhang/discord_quote_bot 
    ```

# Additional Details

- If you're using WatchTower, you'll also want to run to keep both the production and development quote bot running:

    ```
    docker run -d \
      --name watchtower \
      -v /var/run/docker.sock:/var/run/docker.sock \
      v2tec/watchtower --interval 10 cyzhang/discord_quote_bot cyzhang/discord_quote_bot:development
    ```

- If you're running the development branch:
    - Pull the development image: `docker pull cyzhang/discord_quote_bot:development`
    - Set your authentication token as `DISCORD_QUOTEBOT_DEV_TOKEN` in your environment
    - Use the alternate token when starting up the quotebot
    
    ```
    sudo docker run --restart unless-stopped \
    -d -e DISCORD_QUOTEBOT_TOKEN=$DISCORD_QUOTEBOT_DEV_TOKEN \
    cyzhang/discord_quote_bot 
    ```

    
# Additional Notes:

- Builds are automated and can be monitored here: [Docker Hub Build Monitoring](https://hub.docker.com/r/cyzhang/discord_quote_bot/builds/)
- Frame data source from https://github.com/D4RKONION/fatsfvframedatajson
