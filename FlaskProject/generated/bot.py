
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
    print("Bot ready")

@bot.command()
async def hello(ctx):
    await ctx.send("Hello from ble1zx")

bot.run("TOKEN")
