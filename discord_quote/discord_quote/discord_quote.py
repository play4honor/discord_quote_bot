import datetime
import discord
from discord.ext import commands
import asyncio
import json
import re
import logging
import sys
import os

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
    tmp = [d.replace(u'\u241e', ' ') for d in data]
    return u'\u241e'.join(tmp)

# Code
description = '''
            A Bot to provide Basic Quoting functionality for Discord
            '''

bot = commands.Bot(command_prefix='!', description=description)

@bot.event
@asyncio.coroutine
def on_ready():
    log.info(log_msg(['login', bot.user.name, bot.user.id]))

@bot.event
@asyncio.coroutine
def on_server_join():
    log.info(log_msg(['bot join', bot.user.name, bot.user.id, 'server', bot.server.id]))
            
    yield from bot.send_message(bot.get_all_channels().next(), 'yo, we in there')

    log.info(log_msg(['sent_message', 'server_join', ctx.message.channel.name]))
    
@bot.command(pass_context=True)  
@asyncio.coroutine
def me(ctx, *text : str):
    log.info(log_msg(['received_request', 
                      'me',
                      ctx.message.author.name, 
                      ctx.message.channel.name,
                      ' '.join(text)]))

    output = '_{0} {1}_'.format(
                                ctx.message.author.name, 
                                ' '.join(text)
                            )

    log.info(log_msg(['formatted_self', ' '.join(text)]))

    yield from bot.say(output)

    log.info(log_msg(['sent_message', 'me', ctx.message.channel.name]))

    # Clean up request regardless of success
    yield from bot.delete_message(ctx.message)
    log.info(log_msg(['deleted_request', ctx.message.id]))


@bot.command(pass_context=True)  
@asyncio.coroutine
def quote(ctx, msg_id : str, *reply : str):
    log.info(log_msg(['received_request', 
                      'quote',
                      ctx.message.author.name, 
                      ctx.message.channel.name,
                      msg_id]))
    try:
        msg_ = yield from bot.get_message(ctx.message.channel, msg_id)
        
        # Replace triple back ticks with " so it doesn't break formatting when
        # quoting quotes
        msg_.clean_content = msg_.clean_content.replace('```', '|')
        
        log.info(log_msg(['retrieved_quote', 
                          msg_id, 
                          ctx.message.channel.name,
                          msg_.author.name, 
                          msg_.timestamp.strftime("%Y-%m-%d %H:%M:%S"), 
                          ctx.message.author.name, 
                          msg_.clean_content]))

        # Format output message
        if not reply:
            output = '**{0} [{1}] said:** _via {2}_ ```{3}```'.format(
                                msg_.author.name, 
                                msg_.timestamp.strftime("%Y-%m-%d %H:%M:%S"), 
                                ctx.message.author.name, 
                                msg_.clean_content
                        )
        else:
            output = '**{0} [{1}] said:** ```{2}``` **{3}:** {4}'.format(
                                msg_.author.name, 
                                msg_.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                msg_.clean_content, 
                                ctx.message.author.name, 
                                ' '.join(reply)
                        )
        log.info(log_msg(['formatted_quote', ' '.join(reply)]))
            
        yield from bot.say(output)

        log.info(log_msg(['sent_message', 'quote', ctx.message.channel.name]))

    except discord.errors.HTTPException:
        log.warning(['msg_not_found', msg_id, ctx.message.author.name])

        # Return error if message not found.
        yield from bot.say(("Quote not found in this channel ('{0}' "
                            + "requested by "
                            + "{1})").format(msg_id,
                                             ctx.message.author.name))
        log.info(log_msg(['sent_message', 
                          'invalid_quote_request', 
                          ctx.message.channel.name]))
 
    # Clean up request regardless of success
    yield from bot.delete_message(ctx.message)
    log.info(log_msg(['deleted_request', msg_id]))

@bot.command(pass_context=True)  
@asyncio.coroutine
def misquote(ctx , target : discord.User):

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
       
        yield from bot.send_message(ctx.message.author,
                                    ('What would you like to be '
                                     + ' misattributed to ' 
                                     + user.name + '?'))

        log.info(log_msg(['sent_message', 'misquote_dm_request', user.name]))

        def priv(msg):
            return msg.channel.is_private == True

        reply = yield from bot.wait_for_message(timeout=60.0, 
                                                author=ctx.message.author, 
                                                check=priv)

        log.info(log_msg(['received_request', 
                          'misquote_response', 
                          ctx.message.author.name,
                          ctx.message.channel.name,
                          reply.clean_content]))

        faketime = datetime.datetime.now() - datetime.timedelta(minutes=5)

        yield from bot.say('**{0} [{1}] definitely said:** ```{2}```'.format(
                            user.name,
                            faketime.strftime("%Y-%m-%d %H:%M:%S"),
                            reply.clean_content
                            ))

        log.info(log_msg(['sent_message',
                          'misquote',
                           user.name,
                           faketime.strftime('%Y-%m-%d %H:%M:%S'),
                           reply.clean_content ]))
#        else:
#            yield from bot.say("Insufficient Access")
        
    except discord.ext.commands.errors.BadArgument:
        log.warning(log_msg(['user_not_found',
                             target,
                             ctx.message.author.name]))

        yield from bot.say("User not found")

        log.info(log_msg(['sent_message',
                          'invalid_misquote_request',
                          ctx.message.channel.name]))

@bot.command()
@asyncio.coroutine
def frames(char : str, move : str, situ : str=""):
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
                yield from bot.say("{0}'s {1} is **+{2}** on {3}".format(
                    char,
                    move_name,
                    str(frames),
                    s))
                
            elif frames == 0:
                yield from bot.say("{0}'s {1} is **EVEN** on {3}".format(
                    char,
                    move_name,
                    s))
                
            else:
                yield from bot.say("{0}'s {1} is **{2}** on {3}".format(
                    char,
                    move_name,
                    str(frames),
                    s))
                
        elif s in ('startup', 'recovery'):
            frames = move[s]
            yield from bot.say("{0}'s {1} has **{2}** frames of {3}.".format(
                                char,
                                move_name,
                                str(frames),
                                s))

        elif s == 'active':
            frames = move[s]
            yield from bot.say("{0}'s {1} is active for **{2}** frames.".format(
                                char,
                                move_name,
                                str(frames)))
                                
        # Responses for damage and stun
        elif s in ('damage', 'stun'):
            deeps = move[s]
                
            yield from bot.say("{0}'s {1} does **{2}** {3}.".format(
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
            
            yield from bot.say(output)
        
    except KeyError:
        log.warning(log_msg(['frame_data_not_found', 'character',  c]))

        yield from bot.say("Character Not Found")

        log.info(log_msg(['sent_message',
                          'invalid_character_request',
                          ctx.message.channel.name]))

    except IndexError:
        log.warning(log_msg(['frame_data_not_found', 'move',  m]))

        yield from bot.say("Move Not Found")

        log.info(log_msg(['sent_message',
                          'invalid_move_request',
                          ctx.message.channel.name]))

    except UnboundLocalError:
        log.warning(log_msg(['frame_data_not_found', 'situation',  s]))
        
        yield from bot.say("Situation Not Found")

        log.info(log_msg(['sent_message',
                         'invalid_situation_request',
                          ctx.message.channel.name]))

if __name__=='__main__':
    if os.environ['DISCORD_QUOTEBOT_TOKEN']:
        log.info(log_msg(['token_read']))

    log.info(log_msg(['bot_intialize']))
    bot.run(os.environ['DISCORD_QUOTEBOT_TOKEN'])
    
