import datetime
import discord
from discord.ext import commands
import asyncio

description = '''
            A Bot to provide Basic Quoting functionality for Discord
            '''

bot = commands.Bot(command_prefix='!', description=description)

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command(pass_context=True)  
@asyncio.coroutine
def quote(ctx, msg_id : str):
    try:
        msg_ = yield from bot.get_message(ctx.message.channel, msg_id)
        yield from bot.say('_' + msg_.author.name + 
                          ' [' + msg_.timestamp.strftime("%Y-%m-%d %H:%M:%S") + '] said:_ ```' +
                           msg_.clean_content + '```')

    except discord.errors.HTTPException:
        yield from bot.say("Quote not found in this channel")

@bot.command(pass_context=True)  
@asyncio.coroutine
def misquote(ctx , user: discord.User):
    try:
        yield from bot.send_message(ctx.message.author,
                                   'What would you like to be misattributed to ' + user.name + '?')

        def priv(msg):
            return msg.channel.is_private == True

        reply = yield from bot.wait_for_message(timeout=60.0, author=ctx.message.author, check=priv)

        faketime = datetime.datetime.now() - datetime.timedelta(minutes=5)

        yield from bot.say('_' + user.name + 
                      ' [' + faketime.strftime("%Y-%m-%d %H:%M:%S") + '] said:_ ```' +
                       reply.clean_content + '```')
        
    except discord.ext.commands.errors.BadArgument:
        yield from bot.say("User not found")

with open('token.txt', 'r') as tok:
    token = tok.read()

bot.run(token)

