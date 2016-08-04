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
    yield from bot.say('Message ID is ' + msg_id)

bot.run('MjEwNTYyMDMxNjg0ODEyODEx.CoQk0A.UYp9ovxqHMJv10rA2DB96lpClmE')

