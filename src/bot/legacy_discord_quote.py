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

import boto3
import botocore

import src.author_model.author_model as author
from src.bot.utils import log_msg, block_format, parse_msg_url, parse_request, clean_up_request
import src.bot.db as db

from src.bot.webhook_quote import get_hook, webhook_quote
from src.bot.quote import bot_quote

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

    msg_target, reply = parse_request(request)

    # Clean up request regardless of success
    await clean_up_request(ctx, msg_target)

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
        hook = await get_hook(ctx, bot, ctx.channel.id)

        # Use WebHooks if possible
        if hook:
            payload = await webhook_quote(ctx, bot, msg_, *reply)

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
            await bot_quote(ctx, bot, msg_, *reply)

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

    # Enforce normalization
    request = request.lower().strip()

    log.info(log_msg(['received_request',
                    'pin',
                    ctx.message.channel.name,
                    ctx.message.author.name,
                    ctx.message.author.id]))

    # Check if an alias is specified
    if len(request.split(' ')) < 2:
        log.info(log_msg(['sent_message',
                          'invalid_pin_request',
                          ctx.message.channel.name,
                          'No alias specified']))
        await ctx.send('You must specify an alias when pinning.')
        return

    # Parse out message target and reply (if it exists)
    msg_target, alias = parse_request(request, norm_text=True)

    # Clean up request regardless of success
    clean_up_request(ctx, msg_target)

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
    aliases = db.db_execute(f"SELECT alias FROM pins WHERE lower(alias) = \"{alias}\";")
    if len(aliases) > 0:
        log.info(log_msg(['sent_message',
                          'invalid_pin_request',
                          ctx.message.channel.name,
                          'Alias not unique.']))
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
        db.db_execute(
                f"""INSERT INTO pins VALUES (
                "{alias}",
                "{msg_.jump_url}",
                "{ctx.message.author.name}",
                "{ctx.message.created_at}"
            )
            """)
        log.info(log_msg(['insert_successful'] + row))

        # Backup the database to S3
        if bucket:
            db.db_backup()

        # Get, or create a webhook for the context channel
        hook = await get_hook(ctx, bot, ctx.channel.id)

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

async def get(ctx, *, alias:str):
    """Get a pinned message by providing the alias."""

    alias = alias.lower()

    log.info(log_msg(['get_request_received',
                      'pin',
                       alias,
                       ctx.author.name]))

    # Clean up request regardless of success
    try:
        await ctx.message.delete()
        log.info(log_msg(['deleted_request', f'delete \"{alias}\"']))
    except Exception as e:
        log.warning(log_msg(['delete_request_failed', f'delete \"{alias}\"', e]))

    pin = db.db_execute(
            f"SELECT msg_url FROM pins WHERE lower(alias)=\"{alias}\""
    )

    if len(pin) > 0:
        # Get the message url
        msg_url = pin[0][0]

        log.info(log_msg(['retrieved_pin',
                          'pin',
                          alias.lower()]))

        # Quote it
        quote_cmd = ctx.bot.get_command('quote')
        await ctx.invoke(quote_cmd, request=(
            msg_url + f' *using the __**{alias}**__ pin.*'
            )
        )
    else:
        log.info(log_msg(['sent_message',
                          'pin_not_found',
                          ctx.message.channel.name]))
        await ctx.channel.send(f'*{alias}* not found in pins')
        return

async def list(ctx, *, request:str=''):
    """Lists all (or all matching) aliases in the pin database
    and direct messages to the requester (along with a preview).

    If called with no request, list all aliases but does not
    generate a preview for each alias.

    Also works when direct messaging the bot.
    """

    # Normalize the request
    request=request.lower().strip()

    log.info(log_msg(['list_request_received',
                      'pin',
                       request,
                       ctx.author.name]))

    # Clean up request regardless of success
    clean_up_request(ctx, f'list \"{request}"')

    _temp = db.db_execute(
            f"SELECT * FROM pins"
    )

    # First element is alias, second element is msg_url
    try:
        # Matching logic here, also parse msg_urls for previews
        if request != '':
            matching_aliases = [{'alias':x[0], 'msg_id_tuple':parse_msg_url(x[1])}
                                for x in _temp
                                if request in x[0].lower()]
        else:
            matching_aliases = [{'alias':x[0], 'msg_id_tuple':(None, None, None)}
                                for x in _temp]

        log.info(log_msg(['parsed_matching_alias_url_request',
                        'pin',
                        request]))
    except ValueError as e:
        matching_aliases=[]
        log.info(log_msg(['parsed_url_request_failed', f'list \"{request}"']))


    if len(matching_aliases)==0:
        await ctx.message.author.send(f"No aliases matching *{request}*.")

        log.info(log_msg(['no_matches_sent',
                          'pin',
                           request,
                           ctx.author.name,
                           len(matching_aliases)]))
    else:
        # Construct aliases with preview
        out = ''
        for msg in matching_aliases:
            alias = msg['alias']
            guild_id = msg['msg_id_tuple'][0]
            channel_id = msg['msg_id_tuple'][1]
            msg_id = msg['msg_id_tuple'][2]
            try:
                guild = ctx.bot.get_guild(guild_id)
                channel = guild.get_channel(channel_id)

                # Fetch the pinned message
                raw_msg = (
                        await channel.fetch_message(msg_id)
                )

                log.info(log_msg(['retrieved_message', 'pin', channel_id, msg_id]))

                # Grab a 48 character preview
                # (max 25 character alias + 7 filler characters means max line
                # length is 80)
                msg_preview = (
                    raw_msg
                    .content[0:min(len(raw_msg.content), 48)]
                    .replace('\n', ' ')
                    .replace('\r', ' ')
                    .strip()
                )

                # Append to output
                out += '\n' + f"**{alias}** — (*\"{msg_preview}\"*)"

                log.info(log_msg(['generated_preview', 'pin', channel_id, msg_id]))

            except Exception as e:
                out += '\n' + f"**{alias}** — (*No preview.*)"
                log.error(log_msg(['failed_to_preview', 'pin', e]))
                continue

        await ctx.message.author.send(
            "**All matching aliases:**" + out
        )

        log.info(log_msg(['list_matches_sent',
                          'pin',
                          request,
                           ctx.author.name,
                           len(matching_aliases)]))


    return

async def delete(ctx, *, alias:str):
    """Deletes an alias from the set of stored pins.
    """
    alias = alias.lower().strip()

    log.info(log_msg(['delete_request_received',
                      'pin',
                       alias,
                       ctx.author.name]))

    # Clean up request regardless of success
    clean_up_request(ctx, f'delete \"{alias}\"')

    # Check if the alias exists in the pin database
    pin = db.db_execute(
            f"SELECT msg_url FROM pins WHERE lower(alias)=\"{alias}\""
    )

    # If it exists, delete it.
    if len(pin) > 0:
        db.db_execute(
            f"DELETE FROM pins WHERE lower(alias)=\"{alias}\""
        )

        log.info(log_msg(['deleted_pin',
                          'pin',
                          alias.lower()]))

        # Backup the database to S3
        if bucket:
            db.db_backup()


        await ctx.channel.send(f'*{alias}* deleted from pins by **{ctx.author.name}**')
    else:
        log.info(log_msg(['sent_message',
                          'pin_not_found',
                          ctx.message.channel.name]))
        await ctx.channel.send(f'*{alias}* not found in pins')

    return

async def test(ctx):
    """Function for debugging the current status of all the quote commands.
    """

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

