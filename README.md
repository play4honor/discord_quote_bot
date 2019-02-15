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
    - Set your client token as `DISCORD_QUOTEBOT_DEV_TOKEN` in your environment
    - Use the alternate token when starting up the quotebot
    
    ```
    sudo docker run --restart unless-stopped \
    -d -e DISCORD_QUOTEBOT_TOKEN=$DISCORD_QUOTEBOT_DEV_TOKEN \
    cyzhang/discord_quote_bot 
    ```
- If you want to run a personal version of the bot for testing your own changes:
    - Clone this repo and checkout your own branch for making changes (work off the `development` branch)
    - Obtain a client token from Discord:
         - Create a new application [here](https://discordapp.com/developers/applications/)
         - Within the application, create a bot.
         - Log in to Discord and then visit this URL, subbing in the ClientID of your application
         
         ```
         https://discordapp.com/oauth2/authorize?client_id=[ClientID]&scope=bot&permissions=0
         ```
         - Find the Client Token of your bot (this is *not* the client secret and is found on the **bot** page)
    - Set the environment variable to be the client token
    
    ```
    export DISCORD_QUOTEBOT_TOKEN=[ClientToken]
    ```
    
    - Navigate to your local repository and set up the development environment using `venv`
    
    ```
    python3.6 -m venv ./venv
    . ./venv/bin/activate
    pip install -r ./requirements.txt
    ```
    
    - Start your personal quotebot
    
    ```
    cd ./discord_quote/discord_quote
    python discord_quote.py
    ```
    
    - At this point, your personal quote bot should show up in #stuff. You'll need to assign appropriate permissions for it to be used in a channel.
    
    
# Additional Notes:

- Builds are automated and can be monitored here: [Docker Hub Build Monitoring](https://hub.docker.com/r/cyzhang/discord_quote_bot/builds/)
- Frame data source from https://github.com/D4RKONION/fatsfvframedatajson
