import os
import threading
from flask import Flask
import discord
from discord.ext import commands

# Miniaturní webový server pro Render (aby neodpojoval bota kvůli chybějícímu portu)
app = Flask(__name__)

@app.route('/')
def home():
    return "FrostBOT běží zdarma 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Spuštění webového serveru na pozadí
threading.Thread(target=run_web, daemon=True).start()

# Nastavení Discord Bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} je úspěšně připojen a běží!')

# Spuštění bota
token = os.getenv("BOT_TOKEN")
if token:
    bot.run(token)
else:
    print("Chyba: BOT_TOKEN nebyl nalezen v proměnných prostředí!")
