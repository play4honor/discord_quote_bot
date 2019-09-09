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

# Load Frame Data json
with open('sfv.json', 'r') as f:
    moves = json.loads(f.read())

def log_msg(data):
    """
    Accepts a list of data elements, removes the  u'\u241e'character
    from each element, and then joins the elements using u'\u241e'.

    Messages should be constructed in the format:

        {message_type}\u241e{data}

    where {data} should be a \u241e delimited row.
    """
    tmp = [str(d).replace(u'\u241e', ' ') for d in data]
    return u'\u241e'.join(tmp)

# Format a message as a block quotes.
def block_format(message):

    # Find new line positions
    insert_idx = [pos for pos, char in enumerate(message) if char == "\n"]
    insert_idx.insert(0, -1)

    # Insert "> " for block quote formatting
    for offset, i in enumerate(insert_idx):

        message = (message[:i + (2 * offset) + 1] + 
                  "> " + 
                  message[i + (2 * offset) + 1:])

    return(message)

# Code
description = '''
            A Bot to provide Basic Quoting functionality for Discord
            '''

bot = commands.Bot(command_prefix='!', description=description)

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

            await channel.send('yo we in there')


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
    log.info(log_msg(['received_request',
                      'quote',
                      ctx.message.channel.name,
                      ctx.message.author.name,
                      ctx.message.author.id]))

    # Parse out message id and reply (if it exists)
    msg_id = request.split(' ')[0]
    reply = request.split(' ')[1:]

    if '\r' in msg_id or '\n' in msg_id:
      # If weird users decide to separate the msg_id from the reply using a line return
      # clean it up.
      if '\r' in msg_id:
        _temp = msg_id.split('\r')
      else:
        _temp = msg_id.split('\n')

      msg_id = _temp[0].strip()
      reply = [_temp[1].strip()] + request.split(' ')[1:]

    log.info(log_msg(['parsed_request',
                      'quote',
                      ctx.message.channel.name,
                      msg_id,
                      reply]))

    # Clean up request regardless of success
    try:
        await ctx.message.delete()
        log.info(log_msg(['deleted_request', msg_id]))
    except Exception as e:
        log.warning(log_msg(['delete_request_failed', msg_id, e]))
    
    try:
        # Retrieve the message
        msg_ = await ctx.channel.fetch_message(msg_id)
        log.info(log_msg(['retrieved_quote',
                      msg_id,
                      ctx.message.channel.name,
                      msg_.author.name,
                      msg_.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                      ctx.message.author.name,
                      msg_.clean_content]))

        # Get, or create a webhook
        hook = await _get_hook(ctx)

        # Use WebHooks if possible
        if hook:
            payload = await webhook_quote(ctx, msg_, *reply)

            # We need custom handling, so create a Webhook Adapter from our hook
            await hook._adapter.execute_webhook(
                payload={
                    "content":payload,
                    "username" : ctx.guild.me.name,
                    "avatar_url": str(ctx.guild.me.avatar_url)
                }
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
            f"Couldn't quote ({msg_id}) in this channel. " +
            f"Requested by {ctx.message.author.name}."
        )

        log.info(log_msg(['sent_message',
                          'invalid_quote_request',
                          ctx.message.channel.name]))

# Helper function for quote: gets a WebHook
async def _get_hook(ctx):
    # Check for 'Manage WebHook' permission and return if missing permission
    if not ctx.channel.permissions_for(ctx.guild.me).manage_webhooks:
        return

    # Figure out the appropriate webhook
    hook = None
    webhooks = await ctx.channel.webhooks()
    if webhooks:
        # If there's an existing webhook, just use that.
        hook = webhooks[0]
        log.info(log_msg(['webhook_found', hook.name]))
    else:
        log.info(log_msg(['webhook_not_found']))

        # Otherwise, create a webhook.
        hook = await ctx.channel.create_webhook(name=bot.user.name)
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

    output = (
        f"**{msg_.author.name} {action} " +
        f"[{relative_time}](<{msg_.jump_url}>):**\n"+
        block_format(msg_.clean_content) + "\n"
    )

    return(output)

# Helper function for WebHook Quote (quoting quotes)
async def _format_quote(ctx, msg_):
    output = msg_.content

    # Identify the response in the quote without a jump url
    last_responder = re.search('\*\*(.*)\sresponded:\*\*\s', output)

    current_time = arrow.get(ctx.message.created_at)

    # Adjust old relative times
    # First, identify the old times
    old_relative_times = re.findall(
        '(\*\*.*\[(.*)\]\(\<' +
        'https:\/\/discordapp\.com\/channels\/[0-9]*\/[0-9]*\/([0-9]*)'
        +'\>\))',
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
        _author = re.search("^\*\*(.*)\[(.*)\]\ssaid:\*\*", msg_.clean_content)
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
            output = {0}.replace(
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
                "\*\*[A-Za-z0-9]*\s(\[[A-Za-z0-9\s]*\])\sresponded",
                msg_.content
        )

        if _last_response:
            clean_content = clean_content.replace(
                    _last_response.group(1),
                    f"[{_last_response.group(1)}({jump_url})]"
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

@bot.command(pass_context=True)
async def misquote(ctx , target : discord.User):

    log.info(log_msg(['received_request',
                      'misquote',
                      ctx.message.author.name,
                      ctx.message.channel.name,
                      target.name]))

    try:
#        if ctx.message.author.permissions_in(ctx.message.channel.name).administrator:

        user = target
        #if target[1] == "@":
        #    user = target
        #else:
        #    user = ctx.message.server.get_member(target)

        await ctx.message.author.send(
          f"What would you like to be misattributed to {user.name}?"
        )

        log.info(log_msg(['sent_message', 'misquote_dm_request', user.name]))

        def priv(msg):
            return msg.channel.is_private == True

        # Check that this is the right message
        def pred(m):
            return (
                m.author == ctx.message.author 
                and isinstance(m.channel, discord.DMChannel)
            )
        reply = await bot.wait_for('message', check=pred, timeout=60)
#        reply = await bot.wait_for_message(timeout=60.0,
#                                           author=ctx.message.author,
#                                           check=priv)

        log.info(log_msg(['received_request',
                          'misquote_response',
                          ctx.message.author.name,
                          ctx.message.channel.name,
                          reply.clean_content]))

        faketime = (
            datetime.datetime.now() - datetime.timedelta(minutes=5)
        ).strftime("%Y-%m-%d %H:%M:%S")

        await ctx.channel.send(
            f"**{user.name} [{faketime}] definitely said:** \n" +
            block_format(reply.clean_content)
        )

        log.info(log_msg(['sent_message',
                          'misquote',
                           user.name,
                           faketime,
                           reply.clean_content ]))
#        else:
#            yield from bot.say("Insufficient Access")

    except discord.ext.commands.errors.BadArgument:
        log.warning(log_msg(['user_not_found',
                             target,
                             ctx.message.author.name]))

        await bot.say("User not found")

        log.info(log_msg(['sent_message',
                          'invalid_misquote_request',
                          ctx.message.channel.name]))

@bot.command()
async def frames(char : str, move : str, situ : str=""):
    log.info(log_msg(['received_request',
                      'frames',
                      char,
                      move,
                      situ]))
    try:
        c = char.capitalize()
        d,b = move.lower().split('.')
        s = situ.lower()

        # Dictionaries
        char_names = {'Chun-li': 'Chun-Li',
                      'Chun': 'Chun-Li',
                      'Chunli': 'Chun-Li',
                      'Youngzeku':'Zeku (Young)',
                      'Yzeku':'Zeku (Young)',
                      'Fang':'F.A.N.G',
                      'Oldzeku':'Zeku (Old)',
                      'Ozeku':'Zeku (Old)',
                      'Boxer':'Balrog',
                      'Claw':'Vega',
                      'R.mika':'R.Mika',
                      'Mika':'R.Mika',
                      'M.bison':'M.Bison',
                      'Bison':'M.Bison',
                      'Bipson':'M.Bison',
                      'Dictator':'M.Bison'}

        directions = {'stand':'stand',
                      '5':'stand',
                      's':'stand',
                      'st':'stand',
                      'crouch':'crouch',
                      '2':'crouch',
                      'c':'crouch',
                      'cr':'crouch',
                      'jump':'jump',
                      '8':'jump',
                      'j':'jump'}

        buttons = {'hk':'HK',
                   'heavy kick':'HK',
                   'roundhouse':'HK',
                   'mk':'MK',
                   'medium kick':'MK',
                   'forward':'MK',
                   'lk':'LK',
                   'light kick':'LK',
                   'short':'LK',
                   'hp':'HP',
                   'heavy punch':'HP',
                   'fierce':'HP',
                   'mp':'MP',
                   'medium punch':'MP',
                   'strong':'MP',
                   'lp':'LP',
                   'light punch':'LP',
                   'jab':'LP'}

        # Select Move
        if c in char_names.keys():
            char = char_names[c]
        else:
            char = c
        move_name = ' '.join([directions[d], buttons[b]])
        move = moves[char]['moves']['normal'][move_name]

        # Responses for startup, active, recovery
        if s in ('block', 'hit'):
            if s == 'block':
                frames = move['onBlock']

            if s == 'hit':
                frames = move['onHit']

            if frames > 0:
                await bot.say("{0}'s {1} is **+{2}** on {3}".format(
                    char,
                    move_name,
                    str(frames),
                    s))

            elif frames == 0:
                await bot.say("{0}'s {1} is **EVEN** on {3}".format(
                    char,
                    move_name,
                    s))

            else:
                await bot.say("{0}'s {1} is **{2}** on {3}".format(
                    char,
                    move_name,
                    str(frames),
                    s))

        elif s in ('startup', 'recovery'):
            frames = move[s]
            await bot.say("{0}'s {1} has **{2}** frames of {3}.".format(
                                char,
                                move_name,
                                str(frames),
                                s))

        elif s == 'active':
            frames = move[s]
            await bot.say("{0}'s {1} is active for **{2}** frames.".format(
                                char,
                                move_name,
                                str(frames)))

        # Responses for damage and stun
        elif s in ('damage', 'stun'):
            deeps = move[s]

            await bot.say("{0}'s {1} does **{2}** {3}.".format(
                                char,
                                move_name,
                                str(deeps),
                                s))

        # For nothing, or anything else, respond with summary of frame data
        else:
            # Dictionary of key names and nice names for printed results
            dataNames = {'startup': ('Startup', 0),
                         'active': ('Active', 1),
                         'recovery': ('Recovery', 2),
                         'onBlock': ('On Block', 3),
                         'onHit': ('On Hit', 4),
                         'damage': ('Damage', 5),
                         'stun': ('Stun', 6)
                        }

            output = "{0}'s {1} frame data:\n".format(char, move_name)

            # Add to output based on existing frame data
            for x in sorted(dataNames, key=lambda x : dataNames[x][1]):
                output += "{0}: **{1}**, ".format(dataNames[x][0], str(move[x]))

            # Remove last character (extra comma)
            output = output[:-2]

            await bot.say(output)

    except KeyError:
        log.warning(log_msg(['frame_data_not_found', 'character',  c]))

        await bot.say("Character Not Found")

        log.info(log_msg(['sent_message',
                          'invalid_character_request',
                          ctx.message.channel.name]))

    except IndexError:
        log.warning(log_msg(['frame_data_not_found', 'move',  m]))

        await bot.say("Move Not Found")

        log.info(log_msg(['sent_message',
                          'invalid_move_request',
                          ctx.message.channel.name]))

    except UnboundLocalError:
        log.warning(log_msg(['frame_data_not_found', 'situation',  s]))

        await bot.say("Situation Not Found")

        log.info(log_msg(['sent_message',
                         'invalid_situation_request',
                          ctx.message.channel.name]))

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

    # Misquote
    # This seems annoying to test.

    # TEST 6: Me Function
    msg_ = await get_last_real_message()
    me_cmd = ctx.bot.get_command('me')
    await ctx.invoke(me_cmd, 'is testing the quote-bot.')

    await ctx.channel.send('|---END TESTING QUOTE FUNCTIONS---|')


if __name__=='__main__':
    if os.environ['DISCORD_QUOTEBOT_TOKEN']:
        log.info(log_msg(['token_read']))

    log.info(log_msg(['bot_intialize']))
    bot.run(os.environ['DISCORD_QUOTEBOT_TOKEN'])

