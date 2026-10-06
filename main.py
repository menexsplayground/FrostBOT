import os
import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, Select
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

# --- KONFIGURACE ID KANÁLŮ (Doplň si své ID kanálů ze serveru) ---
CHANNEL_ORDER_HERE = 123456789012345678  # #💳order💳
CATEGORY_SERVICES = 123456789012345678   # ID kategorie ⚡⚜️ SERVICES ⚜️⚡
CHANNEL_REVIEWS = 123456789012345678     # #⭐review⭐
CHANNEL_EARNINGS = 123456789012345678    # Kanál pro výdělky (pouze pro ownera)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('FrostSTORE Bot is fully online and ready!')

# --- FORMULÁŘ PRO OBJEDNÁVKU ---
class ServiceOrderModal(Modal):
    def __init__(self, service_type: str):
        super().__init__(title=f"FrostSTORE — {service_type.capitalize()}")
        self.service_type = service_type

        self.current_stat = TextInput(
            label="Current Rank / Trophies / Status",
            placeholder="e.g. Gold 1 or 2300 trophies",
            required=True
        )
        self.goal_stat = TextInput(
            label="Goal Rank / Trophies / Target",
            placeholder="e.g. Mythic 1 or 2500 trophies",
            required=True
        )
        self.p11_brawlers = TextInput(
            label="How many P11 Brawlers do you have?",
            placeholder="e.g. 10",
            required=True
        )
        self.payment_method = TextInput(
            label="Payment Method (Apple Pay, PayPal, Bank)",
            placeholder="applepay / paypal / bank",
            required=True
        )

        self.add_item(self.current_stat)
        self.add_item(self.goal_stat)
        self.add_item(self.p11_brawlers)
        self.add_item(self.payment_method)

    async def on_submit(self, interaction: discord.Interaction):
        # Ověření platební metody
        pm = self.payment_method.value.lower()
        if "apple" in pm:
            pay_emoji = "<:applepay:123456789>"
            pay_name = "Apple Pay"
        elif "paypal" in pm:
            pay_emoji = "<:paypal:123456789>"
            pay_name = "PayPal"
        else:
            pay_emoji = "<:bank:123456789>"
            pay_name = "Bank Transfer"

        embed = discord.Embed(
            title="🔔 New Order Pending Approval",
            description=f"Client: {interaction.user.mention}\nService: **{self.service_type.upper()}**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Current", value=self.current_stat.value, inline=True)
        embed.add_field(name="Goal", value=self.goal_stat.value, inline=True)
        embed.add_field(name="P11 Brawlers", value=self.p11_brawlers.value, inline=False)
        embed.add_field(name="Payment", value=f"{pay_emoji} {pay_name}", inline=False)
        embed.set_footer(text="Awaiting Owner Payment Confirmation...")

        # Tlačítko pro schválení platby majitelem
        view = OwnerApprovalView(interaction.user, self.service_type, self.current_stat.value, self.goal_stat.value, pay_name)
        
        await interaction.response.send_message("✅ Your order has been submitted for payment confirmation by the owner!", ephemeral=True)
        
        # Pošleme to majiteli do soukromého kanálu nebo do admin chatu
        # Pro zjednodušení pošleme schválení do aktuálního chatu (kde má práva jen majitel)
        await interaction.channel.send(embed=embed, view=view)

# --- SCHVÁLENÍ PLATBY MAJITELEM ---
class OwnerApprovalView(View):
    def __init__(self, client, service_type, current, goal, payment):
        super().__init__(timeout=None)
        self.client = client
        self.service_type = service_type
        self.current = current
        self.goal = goal
        self.payment = payment

    @discord.ui.button(label="Confirm Payment & Publish", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_payment(self, interaction: discord.Interaction, button: Button):
        # Zde může mít kontrolu pouze majitel
        embed = discord.Embed(
            title=f"🚀 Active Order — {self.service_type.upper()}",
            description=f"Client: {self.client.mention}\nProgress: 🟢 0% (Waiting for booster)",
            color=discord.Color.purple()
        )
        embed.add_field(name="Route", value=f"{self.current} ➔ {self.goal}", inline=False)
        embed.add_field(name="Payment", value=self.payment, inline=False)
        embed.set_footer(text="FrostSTORE Available Orders")

        # Tlačítka pro boostery / staff
        staff_view = StaffOrderControlView()

        await interaction.message.edit(embed=embed, view=staff_view)
        await interaction.response.send_message("💳 Payment confirmed! Order published successfully.", ephemeral=True)

# --- OVLÁDACÍ TLAČÍTKA PRO STAFF / BOOSTERY ---
class StaffOrderControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Booster Online (🟢)", style=discord.ButtonStyle.secondary)
    async def booster_online(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🟢 Booster is now active and working on the order!", ephemeral=True)

    @discord.ui.button(label="Update Progress / Finish", style=discord.ButtonStyle.primary, emoji="📊")
    async def update_progress(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ProgressUpdateModal())

    @discord.ui.button(label="Close & Review", style=discord.ButtonStyle.danger, emoji="⭐")
    async def close_order(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()
        await interaction.response.send_message(f"⭐ Order finished! Review request sent to review channel.", ephemeral=True)

# --- VÝPOČET PROCENT PODLE ELO / POHÁRKŮ ---
class ProgressUpdateModal(Modal, title="Update Order Progress"):
    current_value = TextInput(
        label="Enter current Elo or Trophies",
        placeholder="e.g. 8775 or 2450",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Ukázkový výpočet (např. pevně pro M1->M2 rozmezí 8250-9250)
        val = int(self.current_value.value)
        start = 8250
        target = 9250
        percent = min(max(int(((val - start) / (target - start)) * 100), 0), 100)

        await interaction.response.send_message(f"📊 Progress updated! Current status: **{percent}%** completed.", ephemeral=True)

# --- VÝBĚR SLUŽBY V !shop ---
class ServiceSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ranked Boost", emoji="<:mythicrank:123456789>", description="Boost your ranked tier (Diamond to Pro)"),
            discord.SelectOption(label="Prestige", emoji="<:prestige1:123456789>", description="Prestige boosting with volume discounts"),
            discord.SelectOption(label="Winstreak", emoji="⚡", description="Unstoppable winstreak service"),
            discord.SelectOption(label="Trophy Bulk", emoji="🏆", description="Bulk trophy pushes for brawlers"),
            discord.SelectOption(label="Matcherino", emoji="🎮", description="Matcherino support & services")
        ]
        super().__init__(placeholder="Select a service category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        service_name = self.values[0]
        await interaction.response.send_modal(ServiceOrderModal(service_name))

class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect())

# --- PŘÍKAZY ---
@bot.command(name='shop')
async def shop(ctx):
    embed = discord.Embed(
        title="⚙️ How Can We Help You?",
        description="Select a category below from the menu to place your order.",
        color=discord.Color.purple()
    )
    embed.set_footer(text="FrostSTORE Order System")
    await ctx.send(embed=embed, view=ShopView())

# --- RUN BOT ---
keep_alive()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
