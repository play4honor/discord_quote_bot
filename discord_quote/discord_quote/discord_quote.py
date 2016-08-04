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


@bot.command()  
@asyncio.coroutine
def quote(msg_id : str):
    if msg_id == "test":
        yield from bot.say("THIS IS ONLY HERE FOR BASIC TESTING")
    else:
        msg_ = bot.get_message(bot.channel, msg_id)
        yield from bot.say(msg_.author.nick + ' said ' + msg_.content)

bot.run('MjEwNTYyMDMxNjg0ODEyODEx.CoQk0A.UYp9ovxqHMJv10rA2DB96lpClmE')

