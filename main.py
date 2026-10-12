import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Select, View

# Miniaturní webový server pro Render (keep-alive)
app = Flask(__name__)

@app.route('/')
def home():
    return "FrostSTORE Brawl Market Běží!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

# Nastavení Discord Bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} je online a připraven pro FrostSTORE!')

# Krok 3: Výběr platby a dokončení
class PaymentView(View):
    def __init__(self, service_type, current_rank, desired_rank):
        super().__init__(timeout=180)
        self.add_item(PaymentSelect(service_type, current_rank, desired_rank))

class PaymentSelect(Select):
    def __init__(self, service_type, current_rank, desired_rank):
        self.service_type = service_type
        self.current_rank = current_rank
        self.desired_rank = desired_rank
        options = [
            discord.SelectOption(label="💳 Credit Card / Apple Pay", description="Standardní platební metoda", emoji="💳"),
            discord.SelectOption(label="💎 PayPal / Crypto", description="Rychlá platba", emoji="💎"),
            discord.SelectOption(label="⭐ In-game Gems", description="Platba v gémch", emoji="⭐")
        ]
        super().__init__(placeholder="Select payment method...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        # Tlačítko/zpráva pro zrušení
        cancel_view = CancelView()
        embed = discord.Embed(
            title="💳 Select Payment Method",
            description=f"**{self.service_type}** — {self.current_rank} ➔ {self.desired_rank}\n💰 **Total Price:** `$4.00`\n\n-------------------------\nSelect how you'd like to pay below.\n\n⚠️ *Small Fee May Apply for non-primary payment methods.*",
            color=discord.Color.from_rgb(45, 45, 55)
        )
        embed.set_footer(text="Powered by FrostSTORE™")
        await interaction.response.send_message(embed=embed, view=cancel_view, ephemeral=True)

# Krok 2: Výběr požadovaného (desired) ranku
class DesiredRankSelect(Select):
    def __init__(self, service_type, current_rank):
        self.service_type = service_type
        self.current_rank = current_rank
        ranks = ["Bronze III", "Silver I", "Silver II", "Silver III", "Gold I", "Gold II", "Gold III", "Diamond I", "Mythic I", "Legendary I", "Masters"]
        options = [discord.SelectOption(label=r, emoji="🏆") for r in ranks]
        super().__init__(placeholder="Select your DESIRED rank...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        desired_rank = self.values[0]
        view = PaymentView(self.service_type, self.current_rank, desired_rank)
        embed = discord.Embed(
            title=f"🏆 {self.service_type} Order",
            description=f"**From:** {self.current_rank}\n**To:** {desired_rank}\n\nSelect your **payment method** below:",
            color=discord.Color.from_rgb(45, 45, 55)
        )
        await interaction.response.edit_message(embed=embed, view=view)

class DesiredRankView(View):
    def __init__(self, service_type, current_rank):
        super().__init__(timeout=180)
        self.add_item(DesiredRankSelect(service_type, current_rank))

# Krok 1: Výběr aktuálního ranku
class CurrentRankSelect(Select):
    def __init__(self, service_type):
        self.service_type = service_type
        ranks = ["Bronze I", "Bronze II", "Bronze III", "Silver I", "Silver II", "Silver III", "Gold I", "Gold II", "Gold III", "Diamond I"]
        options = [discord.SelectOption(label=r, emoji="🪙") for r in ranks]
        super().__init__(placeholder="Select your CURRENT rank...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        current_rank = self.values[0]
        view = DesiredRankView(self.service_type, current_rank)
        embed = discord.Embed(
            title=f"🏆 {self.service_type} Order",
            description=f"**From:** {current_rank}\n\nSelect your **desired rank**:",
            color=discord.Color.from_rgb(45, 45, 55)
        )
        await interaction.response.edit_message(embed=embed, view=view)

class CurrentRankView(View):
    def __init__(self, service_type):
        super().__init__(timeout=180)
        self.add_item(CurrentRankSelect(service_type))

# Hlavní rozevírací menu bota
class MarketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ranked Boost", description="climb the ranked ladder", emoji="👑"),
            discord.SelectOption(label="Trophy Boost", description="push your trophy count", emoji="🏆"),
            discord.SelectOption(label="Winstreak", description="stack up consecutive wins", emoji="🔥"),
            discord.SelectOption(label="Prestige", description="prestige your brawlers", emoji="🛡️"),
            discord.SelectOption(label="Matcherino", description="get your Matcherino pin", emoji="👹")
        ]
        super().__init__(placeholder="Select order type...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        selected_service = self.values[0]
        if selected_service == "Ranked Boost":
            view = CurrentRankView(selected_service)
            embed = discord.Embed(
                title=f"🏆 {selected_service} Order",
                description="Select your **current rank**:",
                color=discord.Color.from_rgb(45, 45, 55)
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(f"Vybrali jste službu: **{selected_service}**. Pokračujeme v objednávce!", ephemeral=True)

class MarketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MarketSelect())

class CancelView(View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancel_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Objednávka byla zrušena.", ephemeral=True)

# Příkaz .panel
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    await ctx.message.delete()
    
    embed = discord.Embed(
        title="📝 Brawl Market — Place an Order",
        description=(
            "👑 **Ranked Boost** — climb the ranked ladder\n"
            "🏆 **Trophy Boost** — push your trophy count\n"
            "🔥 **Winstreak** — stack up consecutive wins\n"
            "🛡️ **Prestige** — prestige your brawlers\n"
            "👹 **Matcherino** — get your Matcherino pin\n\n"
            "✉️ Select your order type below.\n"
            "🟢 Complete payment and a booster will claim your order."
        ),
        color=discord.Color.from_rgb(45, 45, 55)
    )
    embed.set_footer(text="Powered by FrostSTORE™")

    await ctx.send(embed=embed, view=MarketView())

# Spuštění bota
token = os.getenv("BOT_TOKEN")
if token:
    bot.run(token)
else:
    print("Chyba: BOT_TOKEN nebyl nalezen!")
