import os
import discord
from discord.ext import commands
from discord.ui import Select, View, Button, Modal, TextInput
from flask import Flask
from threading import Thread

# --- KEEP ALIVE (Flask) ---
app = Flask('')

@app.route('/')
def home():
    return "FrostBOT is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('FrostBOT is fully online and ready!')

# --- FORMULÁŘ (MODAL) PRO OBJEDNÁVKU ---
class OrderModal(Modal, title="Ranked Boost Order"):
    current_rank = TextInput(
        label="What is your current Rank?",
        placeholder="e.g., Gold 1, Diamond 3...",
        required=True
    )
    rank_goal = TextInput(
        label="What is your Rank goal?",
        placeholder="e.g., Mythic 1, Masters...",
        required=True
    )
    p11_brawlers = TextInput(
        label="How many P11 Brawlers do you have?",
        placeholder="e.g., 15",
        required=True
    )
    payment_method = TextInput(
        label="Choose your Payment Method",
        placeholder="e.g., PayPal, Apple Pay, Crypto...",
        required=True
    )

    async def on_submit(self, interaction: discord.interaction):
        # Vytvoříme Embed s detaily objednávky pro zaměstnance (podobně jako na tvém screenshotu)
        embed = discord.Embed(
            title="🔔 New Order Received",
            color=discord.Color.purple()
        )
        embed.add_field(name="Client", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="Current Rank", value=self.current_rank.value, inline=True)
        embed.add_field(name="Rank Goal", value=self.rank_goal.value, inline=True)
        embed.add_field(name="P11 Brawlers", value=self.p11_brawlers.value, inline=False)
        embed.add_field(name="Payment Method", value=self.payment_method.value, inline=False)
        embed.set_footer(text="FrostSTORE Order System")

        # Odpověď uživateli
        await interaction.response.send_message("✅ Your order form has been submitted successfully! Our staff will contact you shortly.", ephemeral=True)
        
        # Zde může bot poslat zprávu do nějakého konkrétního kanálu pro staff, pokud chceš
        # Např. ctx.guild.get_channel(ID_KANALU).send(embed=embed, view=TicketControlView())

# --- VIEW S TLAČÍTKem PRO OTEVŘENÍ FORMULÁŘE ---
class OrderButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Create Ranked Order", style=discord.ButtonStyle.primary, emoji="🔥")
    async def open_modal(self, interaction: discord.interaction, button: Button):
        # Po kliknutí na tlačítko vyskočí formulář (Modal)
        await interaction.response.send_modal(OrderModal())

# --- PŘÍKAZY ---
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send("Pong! 🏓 Bot běží na Renderu.")

@bot.command(name='shop')
async def shop(ctx):
    embed = discord.Embed(
        title="🚀 Boost & Carry Services",
        description="ℹ️ Click the button below to fill out your order form and get started.",
        color=discord.Color.purple()
    )
    embed.set_footer(text="FrostSTORE Automated System")
    await ctx.send(embed=embed, view=OrderButtonView())

# --- RUN BOT ---
keep_alive()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
