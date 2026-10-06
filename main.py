import os
import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, Select
from flask import Flask
from threading import Thread
from datetime import datetime

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

# Globální proměnné pro sledování výdělků (pro měsíční cíl 200€)
MONTHLY_EARNINGS = 0.0
TODAY_EARNINGS = 0.0
ACTIVE_ORDERS_DATA = []  # Seznam pro živý přehled aktivních objednávek

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('FrostSTORE Bot is fully online and ready with advanced tracking!')

# --- CENÍK A SLEVY FORMATER ---
def get_service_pricing_embed(service_type: str):
    if service_type == "Prestige":
        desc = (
            "🔥 **PRESTIGE SERVICE PRICING & DISCOUNTS** 🔥\n\n"
            "**0 ➔ 1:**\n"
            "• 1x Brawler = 5€\n"
            "• 3x Brawler = 10€ **(🔥 BEST VALUE)**\n"
            "• 5x Brawler = 15€ **(🔥 SUPER DEAL)**\n"
            "• 10x Brawler = 30€ **(🔥 MEGA PACK)**\n\n"
            "**1 ➔ 2:**\n"
            "• 1x Brawler = 15€\n"
            "• 2x Brawler = 25€ **(🔥 SAVE 5€)**\n"
            "• 3x Brawler = 35€ **(🔥 SAVE 10€)**\n"
            "• 5x Brawler = 50€ **(🔥 MASSIVE SAVE)**\n\n"
            "**2 ➔ 3:**\n"
            "• 1x Brawler = 80€\n"
            "• 2x Brawler = 120€ **(🔥 SAVE 40€)**\n"
            "• 3x Brawler = 200€ **(🔥 SAVE 40€)**\n"
            "• 5x Brawler = 300€ **(🔥 ULTIMATE SAVE)**"
        )
    elif service_type == "Ranked Boost":
        desc = (
            "💎 **RANKED BOOST PRICING** 💎\n\n"
            "**Diamond:**\n"
            "• Bronze/Silver/Gold ➔ Diamond = 2€\n"
            "• D1 ➔ D2 = 2€ | D2 ➔ D3 = 2€\n\n"
            "**Mythic:**\n"
            "• D3 ➔ M1 = 3€\n"
            "• M1 ➔ M2 = 4€ | M2 ➔ M3 = 4€\n\n"
            "**Legendary:**\n"
            "• M3 ➔ L1 = 5€\n"
            "• L1 ➔ L2 = 6€ | L2 ➔ L3 = 6€\n\n"
            "**Masters & Pro:**\n"
            "• L3 ➔ Master 1 = 7€\n"
            "• Master 1 ➔ Master 2 = 35€\n"
            "• Master 2 ➔ Master 3 = 75€\n"
            "• Master 3 ➔ PRO = 150€"
        )
    else:
        desc = f"Professional boosting services for **{service_type}** with fast delivery and secure handling."

    embed = discord.Embed(title=f"FrostSTORE — {service_type}", description=desc, color=discord.Color.purple())
    embed.set_footer(text="Powered by FrostSTORE™ — Click below to order!")
    return embed

# --- FORMULÁŘ PRO OBJEDNÁVKU ---
class ServiceOrderModal(Modal):
    def __init__(self, service_type: str):
        super().__init__(title=f"FrostSTORE — {service_type}")
        self.service_type = service_type

        self.current_stat = TextInput(
            label="Current Rank / Trophies / Status",
            placeholder="e.g. Diamond 1 or 8250 Elo",
            required=True
        )
        self.goal_stat = TextInput(
            label="Goal Rank / Trophies / Target",
            placeholder="e.g. Mythic 1 or 9250 Elo",
            required=True
        )
        self.p11_brawlers = TextInput(
            label="How many P11 Brawlers do you have?",
            placeholder="e.g. 3",
            required=True
        )
        self.payment_method = TextInput(
            label="Payment Method (applepay / paypal / bank)",
            placeholder="applepay",
            required=True
        )

        self.add_item(self.current_stat)
        self.add_item(self.goal_stat)
        self.add_item(self.p11_brawlers)
        self.add_item(self.payment_method)

    async def on_submit(self, interaction: discord.Interaction):
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
            description=f"Client: {interaction.user.mention}\nService: **{self.service_type}**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Current", value=self.current_stat.value, inline=True)
        embed.add_field(name="Goal", value=self.goal_stat.value, inline=True)
        embed.add_field(name="P11 Brawlers", value=self.p11_brawlers.value, inline=False)
        embed.add_field(name="Payment", value=f"{pay_emoji} {pay_name}", inline=False)
        embed.set_footer(text="Awaiting Owner Payment Confirmation...")

        view = OwnerApprovalView(
            client=interaction.user,
            service_type=self.service_type,
            current=self.current_stat.value,
            goal=self.goal_stat.value,
            payment=pay_name
        )
        
        await interaction.response.send_message("✅ Your order has been submitted for payment confirmation by the owner!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

# --- SCHVÁLENÍ PLATBY MAJITELEM A ROZCESTNÍK (TICKET + AVAILABLE ORDERS) ---
class OwnerApprovalView(View):
    def __init__(self, client, service_type, current, goal, payment):
        super().__init__(timeout=None)
        self.client = client
        self.service_type = service_type
        self.current = current
        self.goal = goal
        self.payment = payment

    @discord.ui.button(label="Confirm Payment & Create Ticket", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_payment(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.client: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        channel_name = f"order-{self.client.name}".lower()
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        embed = discord.Embed(
            title=f"🚀 Secure Order Ticket — {self.service_type}",
            description=f"Client: {self.client.mention}\nProgress: 🛌 0% (Waiting for booster)\n\n*Note: Use buttons below to interact.*",
            color=discord.Color.purple()
        )
        embed.add_field(name="Route", value=f"{self.current} ➔ {self.goal}", inline=False)
        embed.add_field(name="Payment", value=self.payment, inline=False)
        embed.set_footer(text="FrostSTORE Secure System")

        staff_view = StaffOrderControlView(client_name=self.client.name, service_short=self.service_type)
        ticket_msg = await ticket_channel.send(embed=embed, view=staff_view)

        # Přidání do aktivních objednávek pro živý přehled
        order_item = {
            "client": self.client.name,
            "route": f"{self.current}->{self.goal}",
            "price": "35€",  # Orientační/automatická cena dle domluvy
            "status_emoji": "🛌",
            "percent": 0
        }
        ACTIVE_ORDERS_DATA.append(order_item)

        # Odeslání do kanálu #avalabile-orders pro boostery
        avail_channel = discord.utils.get(guild.text_channels, name="avalabile-orders")
        if avail_channel:
            avail_embed = discord.Embed(
                title="✅ New Available Boost Order!",
                description=f"Service: **{self.service_type}**\nRoute: `{self.current} ➔ {self.goal}`\nClient: {self.client.name}",
                color=discord.Color.green()
            )
            avail_embed.set_footer(text="Check active orders and coordinate in booster chat.")
            await avail_channel.send(embed=avail_embed)

        await interaction.message.delete()
        await interaction.response.send_message(f"💳 Payment confirmed! Secure ticket created: {ticket_channel.mention}", ephemeral=True)

# --- OVLÁDACÍ TLAČÍTKA PRO STAFF V TICKETU ---
class StaffOrderControlView(View):
    def __init__(self, client_name, service_short):
        super().__init__(timeout=None)
        self.client_name = client_name
        self.service_short = service_short

    @discord.ui.button(label="Booster Online (🟢)", style=discord.ButtonStyle.secondary)
    async def booster_online(self, interaction: discord.Interaction, button: Button):
        # Aktualizace stavu na aktivní
        for o in ACTIVE_ORDERS_DATA:
            if o["client"] == self.client_name:
                o["status_emoji"] = "🟢"
        await interaction.response.send_message("🟢 Booster is active and working on this order! Status updated to 🟢.", ephemeral=True)

    @discord.ui.button(label="Update Progress", style=discord.ButtonStyle.primary, emoji="📊")
    async def update_progress(self, interaction: discord.Interaction, button: Button):
        modal = ProgressUpdateModal(client_name=self.client_name, ticket_channel=interaction.channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Close & Review", style=discord.ButtonStyle.danger, emoji="⭐")
    async def close_order(self, interaction: discord.Interaction, button: Button):
        global MONTHLY_EARNINGS, TODAY_EARNINGS
        # Přičtení peněz do earnings (např. fixně nebo podle domluvy, zde simulujeme 35€)
        earned_amount = 35.0
        MONTHLY_EARNINGS += earned_amount
        TODAY_EARNINGS += earned_amount

        # Odebrání z aktivních
        global ACTIVE_ORDERS_DATA
        ACTIVE_ORDERS_DATA = [o for o in ACTIVE_ORDERS_DATA if o["client"] != self.client_name]

        # Odeslání výzvy k recenzi do kanálu review
        guild = interaction.guild
        review_channel = discord.utils.get(guild.text_channels, name="review")
        if review_channel:
            rev_embed = discord.Embed(
                title="⭐ New Completed Order & Review Request",
                description=f"Client **{self.client_name}** has successfully finished their boost order!\nThank you for choosing FrostSTORE™.",
                color=discord.Color.gold()
            )
            await review_channel.send(embed=rev_embed)

        await interaction.channel.send("⭐ Order finished! Review request automatically sent to #review. Archiving ticket...")
        await interaction.message.delete()
        
        # Smazání ticketu po chvíli nebo ponechání
        # await interaction.channel.delete()

# --- VÝPOČET PROCENT A AKTUALIZACE ---
class ProgressUpdateModal(Modal, title="Update Order Progress"):
    current_value = TextInput(
        label="Enter current value (Elo / Trophies)",
        placeholder="e.g. 8775 or 2450",
        required=True
    )

    def __init__(self, client_name, ticket_channel):
        super().__init__()
        self.client_name = client_name
        self.ticket_channel = ticket_channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.current_value.value)
            # Standardní výpočet pro příklad Master (8250 až 9250) nebo obecný rozsah
            start = 8250
            target = 9250
            percent = min(max(int(((val - start) / (target - start)) * 100), 0), 100)

            # Aktualizace v globálním přehledu
            for o in ACTIVE_ORDERS_DATA:
                if o["client"] == self.client_name:
                    o["percent"] = percent
                    o["status_emoji"] = "🟢"

            await interaction.response.send_message(f"📊 Progress updated! Current status: **{percent}%** completed.", ephemeral=True)
            await self.ticket_channel.send(f"📊 **Progress Update:** Current value is `{val}` ➔ **{percent}%** completed.")
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

# --- UNIVERZÁLNÍ TLAČÍTKO PRO KATALOGY ---
class CatalogButtonView(View):
    def __init__(self, service_name: str):
        super().__init__(timeout=None)
        self.service_name = service_name

    @discord.ui.button(label="Order Now", style=discord.ButtonStyle.primary, emoji="🛒")
    async def catalog_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ServiceOrderModal(self.service_name))

# --- PŘÍKAZY PRO SETUP KANÁLŮ ---

@bot.command(name='shop')
@commands.has_permissions(administrator=True)
async def shop(ctx):
    embed = discord.Embed(
        title="❄️ Welcome to FrostSTORE Order Hub ❄️",
        description="Ready to boost your account professionally and securely? Browse our services below or click the button to get started!\n\n"
                    "**Accepted Payments:**\n"
                    "<:applepay:123456789> **Apple Pay**\n"
                    "<:paypal:123456789> **PayPal**\n"
                    "<:bank:123456789> **Bank Transfer**",
        color=discord.Color.purple()
    )
    embed.set_footer(text="FrostSTORE™ — Professional Boosting Service")
    await ctx.send(embed=embed)

@bot.command(name='setup_ranked')
@commands.has_permissions(administrator=True)
async def setup_ranked(ctx):
    embed = get_service_pricing_embed("Ranked Boost")
    await ctx.send(embed=embed, view=CatalogButtonView("Ranked Boost"))

@bot.command(name='setup_prestige')
@commands.has_permissions(administrator=True)
async def setup_prestige(ctx):
    embed = get_service_pricing_embed("Prestige")
    await ctx.send(embed=embed, view=CatalogButtonView("Prestige"))

@bot.command(name='setup_winstreak')
@commands.has_permissions(administrator=True)
async def setup_winstreak(ctx):
    embed = get_service_pricing_embed("Winstreak")
    await ctx.send(embed=embed, view=CatalogButtonView("Winstreak"))

@bot.command(name='setup_trophy')
@commands.has_permissions(administrator=True)
async def setup_trophy(ctx):
    embed = get_service_pricing_embed("Trophy Bulk")
    await ctx.send(embed=embed, view=CatalogButtonView("Trophy Bulk"))

@bot.command(name='setup_matcherino')
@commands.has_permissions(administrator=True)
async def setup_matcherino(ctx):
    embed = get_service_pricing_embed("Matcherino")
    await ctx.send(embed=embed, view=CatalogButtonView("Matcherino"))

# --- AUTOMATICKÝ PANEL PRO EARNINGS (FUTURISTICKÝ DESIGN) ---
@bot.command(name='setup_earnings')
@commands.has_permissions(administrator=True)
async def setup_earnings(ctx):
    # Generování futuristického textového vzhledu pro earnings a aktivní objednávky
    orders_text = ""
    if not ACTIVE_ORDERS_DATA:
        orders_text = "No active orders right now."
    else:
        for o in ACTIVE_ORDERS_DATA:
            orders_text += f"{o['status_emoji']} ({o['client']}) {o['route']} — {o['price']} | {o['percent']}%\n"

    earnings_content = (
        "```ansi\n"
        "\u001b[0;32m╔═══════════════════════════════════════════╗\n"
        f"\u001b[0;32m║  MONTHLY EARNINGS: {MONTHLY_EARNINGS}€ / 200€ (Target)   ║\n"
        f"\u001b[0;32m║  TODAY'S EARNINGS: {TODAY_EARNINGS}€                    ║\n"
        "\u001b[0;32m╚═══════════════════════════════════════════╝\n"
        "```\n"
        "📊 **Active Orders Live Status:**\n"
        f"{orders_text}"
    )
    await ctx.send(earnings_content)

# --- RUN BOT ---
keep_alive()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
