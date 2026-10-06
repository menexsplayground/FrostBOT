import os
import discord
from discord.ext import commands
import google.generativeai as genai

# Nastavení klíčů z Render environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Konfigurace Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# Nastavení Discord bot intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Přihlášen jako {bot.user} (ID: {bot.user.id})")

@bot.command(name="gemini", help="Pošle dotaz na Google Gemini AI.")
async def ask_gemini(ctx, *, prompt: str):
    await ctx.typing()
    try:
        response = model.generate_content(prompt)
        await ctx.send(response.text)
    except Exception as e:
        await ctx.send(f"Došlo k chybě při komunikaci s Gemini: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
