import os
import discord
from discord.ext import commands

# Nastavení intents pro bota
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} je úspěšně přihlášen a připraven!")

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong! 🏓 Bot běží na Renderu.")

# Spuštění bota pomocí tokenu z proměnných prostředí Renderu
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    print("CHYBA: Není nastaven DISCORD_TOKEN v proměnných prostředí!")
else:
    bot.run(TOKEN)
