import os
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands

app = Flask('')

@app.route('/')
def home():
    return "FrostBOT je online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} je úspěšně přihlášen a připraven!")

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong! 🏓 Bot běží na Renderu.")

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN is None:
        print("CHYBA: Není nastaven DISCORD_TOKEN v proměnných prostředí!")
    else:
        keep_alive()
        bot.run(TOKEN)
