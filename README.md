# discord_quote_bot
A bot that brings the "quote" feature to Discord text chat.

To get different versions of this bot, you can pull from Docker Hub:
- **latest** stable version: `docker pull cyzhang/discord_quote_bot:latest`.
- **development** version: `docker pull cyzhang/discord_quote_bot:development`.

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
    cyzhang/discord_quote_bot:latest 
    ```

# Additional Details

## Permissions Needed

- You may need to enable `Manage Webhooks` to get full functionality.


# Deployment

## Development Branch

We maintain a fully functioning (hopefully!) development branch. We should test out changes on this branch before merging into the master. To start up the `quote-bot-dev` bot, follow this set of modified instructions:  

1. Pull the development image: `docker pull cyzhang/discord_quote_bot:development`
2. Set your client token as `DISCORD_QUOTEBOT_DEV_TOKEN` in your environment
3. Use the Client Token for `quote-bot-dev` when starting up the docker image  

    ```
    sudo docker run --restart unless-stopped \
        -d -e DISCORD_QUOTEBOT_TOKEN=$DISCORD_QUOTEBOT_DEV_TOKEN \
        cyzhang/discord_quote_bot:development 
    ```

## Watchtower

You can use the Watchtower image to automatically re-deploy your bot when there are changes to the docker image. This is useful when you have an auto-deployment pipeline setup. In addition to starting the quotebot images, you should run the watchtower image:

    ```
    docker run -d \
      --name watchtower \
      -v /var/run/docker.sock:/var/run/docker.sock \
      v2tec/watchtower --interval 10 cyzhang/discord_quote_bot cyzhang/discord_quote_bot:development
    ```

## Docker Hub Webhook

1. Install [Webhook](https://github.com/adnanh/webhook) on the deploy machine
    - Make sure you have opened the port that Webhook is going to listen on (e.g., port `9000`)
2. Get the `hooks.json` and deploy script
    - For the main distribution, clone this repo ([here](https://github.com/zhangchuck/p4h_webhooks))
3. Run Webhook in terminal
    ```
    sudo -E webhook -hooks p4h_webhooks/hooks.json -verbose
    ```
4. Point the webhook in [Docker Hub](https://cloud.docker.com/repository/docker/cyzhang/discord_quote_bot/webhooks) to the deploy machine's endpoint (e.g., `http://ec2-[id].compute.amazonaws.com:9000/hooks/redeploy-quotebot/`)

## Personal Testing Bot
If you want to run a personal version of the bot for testing your own changes, you can do this without using the docker images.

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

- Frame data source from https://github.com/D4RKONION/fatsfvframedatajson
