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
def misquote(ctx , msg_id : str):
    try:
        msg_ = yield from bot.get_message(ctx.message.channel, msg_id)
        yield from bot.say('_' + msg_.author.name + 
                           ' [' + msg_.timestamp.strftime("%Y-%m-%d %H:%M:%S") + '] said:_ ```' +
                           "Jet fuel can't melt steel beams!" + '```')
    except discord.errors.HTTPException:
        yield from bot.say("Quote not found in this channel")

bot.run('MjEwNTYyMDMxNjg0ODEyODEx.CoQk0A.UYp9ovxqHMJv10rA2DB96lpClmE')

