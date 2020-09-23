# Discord Packages
import discord
from discord.ext import commands

# AWS Packages
import boto3
import botocore

# Other Packages
import logging
import sys
import os

sys.path.append('../../')
from src.bot.utils import log_msg
import src.bot.db as db
import src.bot.legacy_discord_quote as old


#-------------------------------------------------------------------------------
# Configure logging
log = logging.getLogger(__name__)
fmt = logging.Formatter(u'\u241e'.join(['%(asctime)s',
                                        '%(name)s',
                                        '%(levelname)s',
                                        '%(funcName)s',
                                        '%(message)s']))
streamInstance = logging.StreamHandler(stream=sys.stdout)
streamInstance.setFormatter(fmt)
log.addHandler(streamInstance)
log.setLevel(logging.DEBUG)

# --- Initialize S3
# Check to see if we can initialize
session = boto3.Session()
bucket = session.resource('s3').Bucket(os.environ['DISCORD_QUOTEBOT_BUCKET'])

# Check for permissions
try:
    if bucket:
        bucket.load()
except botocore.exceptions.NoCredentialsError as e:
    logging.error(log_msg(['No credentials found', e]))
    session = None
    bucket = None
except botocore.exceptions.ClientError as e:
    logging.error(log_msg(['Bad credentials: could not access bucket', e]))
    session = None
    bucket = None


# Bot Code Starts Here
description = '''
            A Bot to provide Basic Quoting functionality for Discord
            '''

bot = commands.Bot(command_prefix='!', description=description)
db.db_load(bucket)   # Initialize a new database

# --- Bot Functions
@bot.event
async def on_ready():
    log.info(log_msg(['login', bot.user.name, bot.user.id]))

    # Search all visibile channels and send a message letting users know that
    # the bot is online. Only send in text channels that the bot has permission
    # in.
    for channel in bot.get_all_channels():
        if (channel.permissions_for(channel.guild.me).send_messages
            and isinstance(channel, discord.TextChannel)):
            log.info(log_msg([
                'sent_message',
                'channel_join',
                '\\'.join([channel.guild.name, channel.name])]
                )
            )

#            await channel.send('yo we in there')

@bot.command()
async def me(ctx, *text : str):
    """
    """
    await old.me(ctx, *text)

@bot.command(aliases=['q'])
async def quote(ctx, *, request:str):
    """
    Quotes an existing message from the same channel.
    request = (MessageID|MessageURL)
    (Make sure you have Discord's developer mode turned on to get Message IDs)
    """
    await old.quote(ctx, request=request, bot=bot)

@bot.command()
async def misquote(ctx , *target : discord.User):
    """
    """
    pass

# --- Pin commands ---
@bot.command(aliases=['p'])
async def put(ctx, *, request:str):
    """
    Stores an existing message from the same channel as a pin with an alias.
    request = (MessageID|MessageURL) (alias)

    Aliases must be < 25 characters and unique to the server.
    Aliases are case-insensitive.

    (Make sure you have Discord's developer mode turned on to get Message IDs)
    """
    pass

@bot.command(aliases=['g'])
async def get(ctx, *, alias:str):
    """Get a pinned message by providing the alias.
    """
    pass

@bot.command(aliases=['l'])
async def list(ctx, *, request:str=''):
    """Lists all (or all matching) aliases in the pin database
    and direct messages to the requester (along with a preview).

    If called with no request, list all aliases but does not
    generate a preview for each alias.

    Also works when direct messaging the bot.
    """
    pass

@bot.command(aliases=['d'])
async def delete(ctx, *, alias:str):
    """Deletes an alias from the set of stored pins.
    """
    pass

@bot.command()
async def test(ctx):
    """Function for debugging the current status of all the quote commands.
    """
    await old.test(ctx)

if __name__=='__main__':
    if os.environ['DISCORD_QUOTEBOT_TOKEN']:
        log.info(log_msg(['token_read']))

    log.info(log_msg(['bot_intialize']))
    bot.run(os.environ['DISCORD_QUOTEBOT_TOKEN'])
