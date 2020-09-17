import datetime
import discord
from discord.ext import commands
import asyncio
import json
import re
import logging
import sys
import os
import arrow
import random
from pathlib import Path
import sqlite3
import boto3
import botocore

import author_model as author
from utils import log_msg, block_format, parse_msg_url

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

# # Load Frame Data json
# with open('sfv.json', 'r') as f:
#     moves = json.loads(f.read())

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

# --- Database functions
def db_load():
    """Checks if a local copy of the Sqlite3 database exist. If not,
    attempts to download a backup from S3. If there is no backup,
    then it initializes a new Sqlite3 database.

    Tries to create (if it doesn't already exist) the `pins` table.

    Returns the connection to the databse.

    Unless absolutely necessary, don't call this directly.
    Use `db_execute()` instead.
    """

    db_filename = os.environ['DISCORD_QUOTEBOT_DB_FILENAME']
    # Check if the database exists
    if not Path(f'./{db_filename}').exists() and bucket:
        # If missing, attempt to download backup file
        logging.info(log_msg(['db_backup', 'download', 'attempt']))
 
        try:
            bucket.download_file(db_filename, db_filename)
        except botocore.exceptions.ClientError:
            logging.error(log_msg(['db_backup', 'download', 'failed']))

        logging.info(log_msg(['db_backup', 'download', 'successful']))

    if Path(f'./{db_filename}').exists():
        logging.info(log_msg(['database_found']))

    conn = sqlite3.connect(f'./{db_filename}')
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pins (
        alias TEXT, msg_url TEXT, pin_user TEXT, pin_time TEXT
        )
        """
    )

    return(conn)

def db_execute(query):
    """Wrapper to ensure that any queries that are launched at the
    database are launched inside a database context (i.e., the connection
    is closed after the query is run).

    Returns all the results of the query.
    """
    # We define this helper function to make sure that the db is closed
    # after every query. If not, easy way to corrupt the db.
    with db_load() as conn:
        c = conn.cursor()
        c.execute(query)
        return(c.fetchall())

def db_backup():
    """When called, backs up the sqlite database to a pre-specified S3 bucket.
    """
    logging.info(log_msg(['db_backup', 'upload', 'attempt']))

    bucket.download_file(
        './discord_quote_bot_data.db',
        'discord_quote_bot_data.db'
    )

    logging.info(log_msg(['db_backup', 'upload', 'successful']))

# Bot Code Starts Here
description = '''
            A Bot to provide Basic Quoting functionality for Discord
            '''

bot = commands.Bot(command_prefix='!', description=description)
db_load()   # Initialize a new database

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


#@bot.event
#@asyncio.coroutine
#def on_server_join(server):
#    log.info(log_msg(['bot join', bot.user.name, bot.user.id, 'server', bot.server.id]))
#
#    all_channels = server.get_all_channels()
#    for channels in all_channels:
#        yield from bot.send_message(channel, 'yo, we in there')
#
#    log.info(log_msg(['sent_message', 'server_join', ctx.message.channel.name]))

@bot.command()
async def me(ctx, *text : str):
    log.info(log_msg(['received_request',
                      'me',
                      ctx.message.author.name,
                      ctx.message.channel.name,
                      ' '.join(text)]))

    output = f"_{ctx.message.author.name} { ' '.join(text) }_"

    log.info(log_msg(['formatted_self', ' '.join(text)]))

    await ctx.channel.send(output)

    log.info(log_msg(['sent_message', 'me', ctx.message.channel.name]))

    # Clean up request regardless of success
    try:
        await ctx.message.delete()
        log.info(log_msg(['deleted_request', ctx.message.id]))
    except Exception as e:
        log.warning(log_msg(['delete_request_failed', ctx.message.id, e]))

@bot.command(aliases=['q'])
async def quote(ctx, *, request:str):
    """
    Quotes an existing message from the same channel.
    request = (MessageID|MessageURL)
    (Make sure you have Discord's developer mode turned on to get Message IDs)
    """

    log.info(log_msg(['received_request',
                      'quote',
                      ctx.message.channel.name,
                      ctx.message.author.name,
                      ctx.message.author.id]))

    # Parse out message target and reply (if it exists)
    msg_target = request.split(' ')[0]
    reply = request.split(' ')[1:]

    # Clean up request regardless of success
    try:
        await ctx.message.delete()
        log.info(log_msg(['deleted_request', msg_target]))
    except Exception as e:
        log.warning(log_msg(['delete_request_failed', msg_target, e]))

    if '\r' in msg_target or '\n' in msg_target:
      # If weird users decide to separate the msg_id from the reply using a line return
      # clean it up.
      if '\r' in msg_target:
        _temp = msg_target.split('\r')
      else:
        _temp = msg_target.split('\n')

      msg_target = _temp[0].strip()
      reply = [_temp[1].strip()] + request.split(' ')[1:]

    # If the Message target is numeric, assume it's the ID
    # if not assume it's the message url
    if msg_target.isnumeric():
        msg_id = msg_target
        channel_id = ctx.channel.id # if numeric, then channel is same as context

        log.info(log_msg(['parsed_id_request',
                        'quote',
                        ctx.message.channel.name,
                        msg_id,
                        reply]))
    else:
        try:
            _, channel_id, msg_id = parse_msg_url(msg_target)
        except ValueError as e:
            log.info(log_msg(['parsed_url_request_failed', msg_target]))
            return


        log.info(log_msg(['parsed_url_request',
                        'quote',
                        ctx.message.channel.name,
                        msg_target,
                        msg_id,
                        reply]))

    try:
        # Retrieve the message
        msg_ = await ctx.guild.get_channel(channel_id).fetch_message(msg_id)
        log.info(log_msg(['retrieved_quote',
                      msg_id,
                      ctx.guild.get_channel(channel_id).name,
                      msg_.author.name,
                      msg_.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                      ctx.message.author.name,
                      msg_.clean_content]))

        # Get, or create a webhook for the context channel
        hook = await _get_hook(ctx, ctx.channel.id)

        # Use WebHooks if possible
        if hook:
            payload = await webhook_quote(ctx, msg_, *reply)

            # We retain the output (so we can reference it, if necessary)
            out = await hook.send(
                content=payload,
                username=ctx.guild.me.name,
                avatar_url=str(ctx.guild.me.avatar_url),
                files=[await attachment.to_file() for attachment in msg_.attachments],
                wait=True
            )

            log.info(log_msg(['sent_webhook_message',
                              'quote',
                              ctx.message.channel.name]))

        else:
            await bot_quote(ctx, msg_, *reply)

    except discord.errors.HTTPException as e:
        log.warning(['msg_not_found', msg_id, ctx.message.author.mention, e])

        # Return error if message not found.
        await ctx.channel.send(
            f"Couldn't quote ({msg_id}) from channel {channel_id}. " +
            f"Requested by {ctx.message.author.name}."
        )

        log.info(log_msg(['sent_message',
                          'invalid_quote_request',
                          ctx.message.channel.name]))

# Helper function for quote: gets a WebHook
async def _get_hook(ctx, channel_id=None):
    # If no specific channel_id is specified, then we want the channel of
    # the ctx
    if not channel_id:
        channel = ctx.channel
    else:
        channel = ctx.guild.get_channel(channel_id)

    # Check for 'Manage WebHook' permission and return if missing permission
    if not channel.permissions_for(ctx.guild.me).manage_webhooks:
        return

    # Figure out the appropriate webhook
    hook = None
    webhooks = await channel.webhooks()
    if webhooks:
        # If there's an existing webhook, just use that.
        hook = webhooks[0]
        log.info(log_msg(['webhook_found', hook.name]))
    else:
        log.info(log_msg(['webhook_not_found']))

        # Otherwise, create a webhook.
        hook = await channel.create_webhook(name=bot.user.name)
        log.info(log_msg(['webhook_created', hook.name]))

    return(hook)

async def webhook_quote(ctx, msg_, *reply: str):
    # This version depends on everything being well quoted (e.g., with jumpurls)
    # If the message that has been passed is assigned to the bot, then it is a
    # previous quote.
    quote = (msg_.author.name == bot.user.name)
    if not quote:
        if reply:
            output = (
                await _format_message(ctx, msg_, 'said') +
                f"**{ctx.message.author.name} responded:** {' '.join(reply)}"
            )
        if not reply:
            output = (
                await _format_message(ctx, msg_, 'said') +
                f"_via {ctx.message.author.name}_"
            )
    elif quote:

        if reply:
            output = (
                await _format_quote(ctx, msg_) +
                f"\n**{ctx.message.author.name} responded:** {' '.join(reply)}"
            )
        elif not reply:
            output = await _format_quote(ctx, msg_)
    else:
        pass

    return(output)

# Helper function for WebHook Quote (quoting simple messages)
async def _format_message(ctx, msg_, action):
    # Figure out the respective times
    current_time = arrow.get(ctx.message.created_at)
    original_message_time = arrow.get(msg_.created_at)
    relative_time = original_message_time.humanize(current_time)

    # Construct the channel jump_url
    channel_url = (
            f"https://discord.com/channels/"
        f"{msg_.guild.id}/{msg_.channel.id}"
    )

    output = (
        f"**{msg_.author.name} {action} " +
        f"[{relative_time}](<{msg_.jump_url}>) " +
        f"in [#{msg_.channel.name}](<{channel_url}>):**\n"+
        block_format(msg_.clean_content) + "\n"
    )

    return(output)

# Helper function for WebHook Quote (quoting quotes)
async def _format_quote(ctx, msg_):
    output = msg_.content

    # Identify the response in the quote without a jump url
    last_responder = re.search(r'\*\*(.*)\sresponded:\*\*\s', output)

    current_time = arrow.get(ctx.message.created_at)

    # Adjust old relative times
    # First, identify the old times
    old_relative_times = re.findall(
        r'(\*\*.*\[(.*)\]\(\<' +
        r'https:\/\/discordapp\.com\/channels\/[0-9]*\/[0-9]*\/([0-9]*)' +
        r'\>\))',
        output
    )

    # Now, re-humanize these times:
    if old_relative_times:
        log.info(log_msg(['old_relative_times', 'found']))
        for i in range(len(old_relative_times)):
            _temp = old_relative_times[i]

            # initialize the target (_old_speaker)
            # and the new content (_new_speaker)
            _old_speaker = _temp[0]
            _new_speaker = _temp[0]

            # get the associated old message
            _old_msg = await ctx.channel.fetch_message(_temp[2])
            log.info(log_msg(['retrieved_quote',
                          _old_msg.id,
                          ctx.message.channel.name,
                          _old_msg.author.name,
                          _old_msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                          ctx.message.author.name,
                          _old_msg.clean_content]))

            # rehumanize the time
            _old_msg_time = arrow.get(_old_msg.created_at)
            _new_relative_time = _old_msg_time.humanize(current_time)

            # format the replacement string
            _new_speaker = _new_speaker.replace(_temp[1], _new_relative_time)

            # update the output
            output = output.replace(_old_speaker, _new_speaker)


    # Edit in the new relative time for the last response
    quotebot_message_time = arrow.get(msg_.created_at)
    relative_time = quotebot_message_time.humanize(current_time)

    # Append the jump url into the quote
    if last_responder:
        _old_speaker = f"**{last_responder.group(1)} responded:**"
        _new_speaker = (
            f"**{last_responder.group(1)} responded " +
            f"[{relative_time}](<{msg_.jump_url}>):**"
        )

        output = output.replace(_old_speaker, _new_speaker)

    return(output)

async def bot_quote(ctx, msg_, *reply : str):
    # This is the old way to quote things, if you don't have the 'Manage
    # WebHooks' permission, but you have a bot user, then this is what will be
    # used.

    quote = False
    author = msg_.author.name
    message_time = msg_.created_at.strftime("%Y-%m-%d %H:%M:%S")

    # If previously quoted, find the original author
    if msg_.author.name == bot.user.name:
        quote = True

        # Run a regex search for the author name and if you can find it
        # re-attribute. If you can't find it, it'll just be the bot's name
        _author = re.search(r"^\*\*(.*)\[(.*)\]\ssaid:\*\*", msg_.clean_content)
        if _author:
            author = _author.group(1)
            log.info(log_msg(['found_original_author', msg_.id, author]))
            message_time = _author.group(2)
            log.info(log_msg(['found_original_timestamp', msg_.id, message_time]))

    clean_content = msg_.clean_content

    # Format output message, handling replies and quotes
    if not reply and not quote:
        log.info(log_msg(['formatting_quote', 'noreply|noquote']))
        # Simplest case, just quoting a non-quotebot message, with no reply
        output = (
            f"**{author} [{message_time}] said:** _via " +
            f"{ctx.message.author.name}_\n" + 
            block_format(clean_content)
        )
    elif not reply and quote:
        log.info(log_msg(['formatting_quote', 'noreply|quote']))

        # Find the original quoter
        _quoter = re.search("__via.*?__", msg_.content)
        if _quoter:
            # Replace the original quoter with the new quoter
            output = msg_.content.replace(
                _quoter.group(0),
                f"__via {ctx.message.author.name}__"
            )
        else:
            # If the regex breaks, just forward the old message.
            output = msg_.content
    elif reply and quote:
        log.info(log_msg(['formatting_quote', 'reply|quote']))

        # Detect Last Response so we can hyperlink
        _last_response = re.search(
                r"\*\*[A-Za-z0-9]*\s(\[[A-Za-z0-9\s]*\])\sresponded",
                msg_.content
        )

        if _last_response:
            clean_content = clean_content.replace(
                    _last_response.group(1),
                    f"[{_last_response.group(1)}({msg_.jump_url})]"
            )

        # Reply to a quotebot quote with a reply
        output = (
            f"{clean_content}\n**{ctx.message.author.name} " +
            f"[{ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] " +
            f"responded:** {' '.join(reply)}"
        )
    else:
        log.info(log_msg(['formatting_quote', 'reply|quote']))

        output = (
                f"**{author} [{msg_.created_at.strftime('%Y-%m-%d %H:%M:%S')}] " +
                f"said:** \n" +
                block_format(clean_content) +
                "\n" +
                f"**{ctx.message.author.name} " +
                f"[{ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] " +
                f"responded:** {' '.join(reply)}"
        )

    log.info(log_msg(['formatted_quote', ' '.join(reply)]))

    await ctx.channel.send(output)

    log.info(log_msg(['sent_message', 'quote', ctx.message.channel.name]))

@bot.command()
async def misquote(ctx , *target : discord.User):
    # Helper to check that this is the right message
    def pred(m):
        return (
            m.author == ctx.message.author 
            and isinstance(m.channel, discord.DMChannel)
        )
    try:
        if len(target) > 1:
            raise ValueError("Must provide 0 or 1 authors")

        if len(target) == 1:
            name = target[0].name
        else:
            name = 'a predictively assigned user'

        log.info(log_msg(['received_request',
                        'misquote',
                        ctx.message.author.name,
                        ctx.message.channel.name,
                        name]))

    
        # DM requester to get message to misattribute
        await ctx.message.author.send(
            f"What would you like to be misattributed to {name}?"
        )
        log.info(log_msg(['sent_message', 'misquote_dm_request', ctx.message.author.name]))

        reply = await bot.wait_for('message', check=pred, timeout=60)
        log.info(log_msg(['received_request',
                          'misquote_response',
                          ctx.message.author.name,
                          ctx.message.channel.name,
                          reply.clean_content]))

        # Generate Fake Timestamp for Message
        fakediff = datetime.timedelta(minutes=random.randint(2, 59))
        faketime = datetime.datetime.utcnow() - fakediff

        # predict author if unspecified
        if len(target) == 1:
            response = (f"**{name} definitely said {int(fakediff.seconds/60)} minutes ago:** \n" +
                            block_format(reply.clean_content)
                        )
        else:
            log.info(log_msg(['no_requested_author']))

            user_id, likelihood = author.get_best_author_id(reply.clean_content, faketime.hour)
            user = await bot.fetch_user(user_id)
            name = user.name
            
            log.info(log_msg(['predicted_author',
                            'best_author_id',
                            user,
                            likelihood]))

            response = (f"**{name} probably *({likelihood*100:.2f}%)* said " +
                            f"{int(fakediff.seconds/60)} minutes ago:** \n" +
                            block_format(reply.clean_content)
                        )

        await ctx.channel.send(
            response
        )

        log.info(log_msg(['sent_message',
                          'misquote',
                           name,
                           faketime,
                           response]))

    except discord.ext.commands.errors.BadArgument:
        log.warning(log_msg(['user_not_found',
                             target,
                             ctx.message.author.name]))

        await ctx.message.author.send("User not found")

        log.info(log_msg(['sent_message',
                          'invalid_misquote_request',
                          ctx.message.channel.name]))

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
    log.info(log_msg(['received_request',
                      'quote',
                      ctx.message.channel.name,
                      ctx.message.author.name,
                      ctx.message.author.id]))

    # Parse out message target and reply (if it exists)
    msg_target = request.split(' ')[0]
    alias = ' '.join(request.split(' ')[1:])

    # Clean up request regardless of success
    try:
        await ctx.message.delete()
        log.info(log_msg(['deleted_request', msg_target]))
    except Exception as e:
        log.warning(log_msg(['delete_request_failed', msg_target, e]))

    if '\r' in msg_target or '\n' in msg_target:
      # If weird users decide to separate the msg_id from the reply using a line return
      # clean it up.
      if '\r' in msg_target:
        _temp = msg_target.split('\r')
      else:
        _temp = msg_target.split('\n')

      msg_target = _temp[0].strip()
      alias = ' '.join([_temp[1].strip()] + request.split(' ')[1:]).lower()

    log.info(log_msg(['received_request',
                      'pin',
                      ctx.message.channel.name,
                      ctx.message.author.name,
                      ctx.message.author.id]))

    if len(alias) == 0:
        log.info(log_msg(['sent_message',
                          'invalid_pin_request',
                          ctx.message.channel.name,
                          'No alias specified']))
        await ctx.send('You must specify an alias when pinning.')
        return
    
    if len(alias) > 25:
        log.info(log_msg(['sent_message',
                          'invalid_pin_request',
                          ctx.message.channel.name,
                          'Alias too long.']))
        await ctx.send('Your alias must be <=25 characters.')
        return

    # Check if alias already exists
    ### MAYBE WE SHOULD JUST SET A PRIMARY KEY IN THE SCHEMA AND HANDLE THE
    ### SQLITE ERROR
    aliases = db_execute(f"SELECT alias FROM pins WHERE alias = \"{alias}\";")
    if len(aliases) > 0:
        log.info(log_msg(['sent_message',
                          'invalid_pin_request',
                          ctx.message.channel.name,
                          'Alias too long.']))
        await ctx.send(f'*{alias}* has already been used as a pin alias')
        return

    # If the Message target is numeric, assume it's the ID
    # if not assume it's the message url
    if msg_target.isnumeric():
        msg_id = msg_target
        channel_id = ctx.channel.id # if numeric, then channel is same as context

        log.info(log_msg(['parsed_id_request',
                        'pin',
                        ctx.message.channel.name,
                        msg_id]))
    else:
        try:
            _, channel_id, msg_id = parse_msg_url(msg_target)
        except ValueError as e:
            log.info(log_msg(['parsed_url_request_failed', msg_target]))
            return


        log.info(log_msg(['parsed_url_request',
                        'pin',
                        ctx.message.channel.name,
                        msg_target,
                        msg_id]))

    try:
        # Retrieve the message
        msg_ = await ctx.guild.get_channel(channel_id).fetch_message(msg_id)
        log.info(log_msg(['retrieved_quote',
                      msg_id,
                      ctx.guild.get_channel(channel_id).name,
                      msg_.author.name,
                      msg_.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                      ctx.message.author.name,
                      msg_.clean_content]))

        # Store the message
        row = [alias, msg_.jump_url, ctx.message.author.name, ctx.message.created_at]
        db_execute(
                f"""INSERT INTO pins VALUES (
                "{alias}",
                "{msg_.jump_url}",
                "{ctx.message.author.name}",
                "{ctx.message.created_at}"
            )
            """)
        
        # Backup the database to S3
        if bucket:
            db_backup()

        # Get, or create a webhook for the context channel
        hook = await _get_hook(ctx, ctx.channel.id)

        # Use WebHooks if possible
        if hook:
            payload = (
                f"**{ctx.message.author.name}** just pinned " +
                f"**{msg_.author.name}'s** [message](<{msg_.jump_url}>) to "+
                f"*{alias}*"
            )

            out = await hook.send(
                content=payload,
                username=ctx.guild.me.name,
                avatar_url=str(ctx.guild.me.avatar_url),
                wait=True
            )

            log.info(log_msg(['sent_webhook_message',
                              'pin successful',
                              ctx.message.channel.name]))

        else:
            payload = (
                f"**{ctx.message.author.name}** just pinned " +
                f"**{msg_.author.name}'s** message to "+
                f"*{alias}*"
            )
            await ctx.channel.send(payload)
            log.info(log_msg(['sent_message',
                              'pin successful',
                              ctx.message.channel.name]))

    except discord.errors.HTTPException as e:
        log.warning(['msg_not_found', msg_id, ctx.message.author.mention, e])

        # Return error if message not found.
        await ctx.channel.send(
            f"Couldn't find ({msg_id}) from channel {channel_id}. " +
            f"Requested by {ctx.message.author.name}."
        )

        log.info(log_msg(['sent_message',
                          'invalid_pin_request',
                          ctx.message.channel.name]))

@bot.command(aliases=['g'])
async def get(ctx, *, request:str):
    pin = db_execute(
            f"SELECT msg_url FROM pins WHERE alias=\"{request.lower()}\""
    )
    if len(pin) > 0:
        # Get the message url
        msg_url = pin[0][0]

        log.info(log_msg(['retrieved_pin',
                          'pin',
                          request.lower()]))

        # Quote it
        quote_cmd = ctx.bot.get_command('quote')
        await ctx.invoke(quote_cmd, request=msg_url)
    else:
        log.info(log_msg(['sent_message',
                          'pin_not_found',
                          ctx.message.channel.name]))
        await ctx.channel.send(f'*{request}* not found in pins')
        return

@bot.command(aliases=['l'])
async def list(ctx, *, request:str=''):
    """Lists all (or all matching) aliases in the pin database
    and direct messages to the requester."""

    log.info(log_msg(['list_request_received',
                      'pin',
                       request,
                       ctx.author.name]))

    # Clean up request regardless of success
    try:
        await ctx.message.delete()
        log.info(log_msg(['deleted_request', f'list \"{request}\"']))
    except Exception as e:
        log.warning(log_msg(['delete_request_failed', f'list \"{request}\"', e]))

    _temp = db_execute(
            f"SELECT alias FROM pins"
    )

    all_aliases = [x[0] for x in _temp]

    ### SKELETON: Add matching logic here
    matching_aliases = all_aliases

    await ctx.message.author.send(
            "All matching aliases:\n\n\t" +
            '\n    '.join(all_aliases)
        )

    log.info(log_msg(['list_matches_sent',
                      'pin',
                       request,
                       ctx.author.name,
                       len(matching_aliases)]))

    return

@bot.command()
async def test(ctx):
    # Function for debugging the current status of all the quote commands.

    # --- Helper functions ---
    async def get_last_real_message():
        # Get the last message in the channel from a real person.
        # We need to skip the initial !test request.
        counter = 0
        async for elem in ctx.channel.history():
            if not elem.author.bot:
                counter += 1
                if counter > 1:
                    return(elem)

    async def get_last_message():
        # Helper function to test quoting quotes
        # Get the last message in the channel (not including the request)
        messages = await ctx.channel.history(limit=2).flatten()
        return(messages[1])

    # --- Tests ---
    # Get the last real message
    msg_ = await get_last_real_message()

    log.debug(msg_)

    # Grab the command
    quote_cmd = ctx.bot.get_command('quote')

    await ctx.channel.send('|---TESTING QUOTE FUNCTIONS---|')
    # TEST 1: Quote without a reply
    await ctx.invoke(quote_cmd, request=f'{msg_.id}')

    # TEST 2: Quote with a reply
    await ctx.invoke(quote_cmd
            , request=f'{msg_.id} Testing quote + reply functionality.')

    # TEST 3: Quote a quote without a reply
    msg_ = await get_last_message()
    await ctx.invoke(quote_cmd, request=f'{msg_.id}')

    # TEST 4: Quote a quote with a reply
    msg_ = await get_last_message()
    await ctx.invoke(quote_cmd
            , request=f'{msg_.id} Testing quoting a quote, with a reply.')

    # TEST 5: Quote a quote with a reply with a reply with annoying text
    msg_ = await get_last_message()
    await ctx.invoke(quote_cmd,
            request = (
                f'{msg_.id} Quoting a quote with a reply, with a '+
                '```codeblock``` in the reply and a double quote \" '+
                'and a single quote \'.'
            )
    )

    # TEST 6: Quote without a reply, via URL quoting
    await ctx.invoke(quote_cmd, request=f'{msg_.jump_url}')

    # TEST 7: Quote with a reply, via URL quoting
    await ctx.invoke(quote_cmd
            , request=f'{msg_.jump_url} Testing quote + reply functionality (via URL quoting).')

    # TEST 8: Quote a quote without a reply, via URL quoting
    msg_ = await get_last_message()
    await ctx.invoke(quote_cmd, request=f'{msg_.jump_url}')

    # TEST 9: Quote a quote with a reply, via URL quoting
    msg_ = await get_last_message()
    await ctx.invoke(quote_cmd
            , request=f'{msg_.jump_url} Testing quoting a quote, with a reply (via URL quoting).')
    # Misquote
    # This seems annoying to test.

    # TEST 10: Me Function
    msg_ = await get_last_real_message()
    me_cmd = ctx.bot.get_command('me')
    await ctx.invoke(me_cmd, 'is testing the quote-bot.')

    # TEST 11
    # This test may not work if the bot is not in P4H
    await ctx.invoke(quote_cmd
            , request=f'https://discord.com/channels/106536439809859584/202198069691940865/738132703253233735')

    await ctx.channel.send('|---END TESTING QUOTE FUNCTIONS---|')

if __name__=='__main__':
    if os.environ['DISCORD_QUOTEBOT_TOKEN']:
        log.info(log_msg(['token_read']))

    log.info(log_msg(['bot_intialize']))
    bot.run(os.environ['DISCORD_QUOTEBOT_TOKEN'])

