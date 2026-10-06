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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('FrostSTORE Bot is fully online and ready!')

# --- FORMULÁŘ PRO OBJEDNÁVKU ---
class ServiceOrderModal(Modal):
    def __init__(self, service_type: str):
        super().__init__(title=f"FrostSTORE — {service_type}")
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

        view = OwnerApprovalView(interaction.user, self.service_type, self.current_stat.value, self.goal_stat.value, pay_name)
        
        await interaction.response.send_message("✅ Your order has been submitted for payment confirmation by the owner!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

# --- SCHVÁLENÍ PLATBY MAJITELEM A VYTVOŘENÍ BEZPEČNÉHO TICKETU ---
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
            description=f"Client: {self.client.mention}\nProgress: 🟢 0% (Waiting for booster)\n\n*Note: Use buttons below to interact.*",
            color=discord.Color.purple()
        )
        embed.add_field(name="Route", value=f"{self.current} ➔ {self.goal}", inline=False)
        embed.add_field(name="Payment", value=self.payment, inline=False)
        embed.set_footer(text="FrostSTORE Secure System — No Direct Typing Allowed")

        staff_view = StaffOrderControlView()
        await ticket_channel.send(embed=embed, view=staff_view)

        await interaction.message.delete()
        await interaction.response.send_message(f"💳 Payment confirmed! Secure ticket created: {ticket_channel.mention}", ephemeral=True)

# --- OVLÁDACÍ TLAČÍTKA PRO STAFF V TICKETU ---
class StaffOrderControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Booster Online (🟢)", style=discord.ButtonStyle.secondary)
    async def booster_online(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🟢 Booster is active and working on this order!", ephemeral=True)

    @discord.ui.button(label="Update Progress", style=discord.ButtonStyle.primary, emoji="📊")
    async def update_progress(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ProgressUpdateModal())

    @discord.ui.button(label="Close & Review", style=discord.ButtonStyle.danger, emoji="⭐")
    async def close_order(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send("⭐ Order finished! Review request sent and ticket will be archived.")
        await interaction.message.delete()

# --- VÝPOČET PROCENT ---
class ProgressUpdateModal(Modal, title="Update Order Progress"):
    current_value = TextInput(
        label="Enter current Elo or Trophies",
        placeholder="e.g. 8775 or 2450",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.current_value.value)
            start = 8250
            target = 9250
            percent = min(max(int(((val - start) / (target - start)) * 100), 0), 100)
            await interaction.response.send_message(f"📊 Progress updated! Current status: **{percent}%** completed.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

# --- UNIVERZÁLNÍ TLAČÍTKO PRO KATALOGOVÉ KANÁLY ---
class CatalogButtonView(View):
    def __init__(self, service_name: str):
        super().__init__(timeout=None)
        self.service_name = service_name

    @discord.ui.button(label="Order Now", style=discord.ButtonStyle.primary, emoji="🛒")
    async def catalog_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ServiceOrderModal(self.service_name))

# --- PŘÍKAZY PRO NASTAVENÍ KANÁLŮ ---

@bot.command(name='setup_order')
@commands.has_permissions(administrator=True)
async def setup_order(ctx):
    embed = discord.Embed(
        title="🛒 Welcome to FrostSTORE Order Hub",
        description="Ready to boost your account? Follow the steps below to place your order securely.\n\n"
                    "**1. Browse Services**\n"
                    "Head over to our **SERVICES** category (`#ranked`, `#prestige`, `#winstreak`, etc.).\n\n"
                    "**2. Click & Fill Form**\n"
                    "Click the **Order Now** button under your desired service. A form will pop up for you to fill in your current stats, goals, and brawlers.\n\n"
                    "**3. Payment Methods**\n"
                    "We accept secure payments via:\n"
                    "<:applepay:123456789> **Apple Pay**\n"
                    "<:paypal:123456789> **PayPal**\n"
                    "<:bank:123456789> **Bank Transfer**\n\n"
                    "**4. Secure Ticket**\n"
                    "Once the owner confirms your payment, a private secure ticket will be created automatically for your boost!",
        color=discord.Color.purple()
    )
    embed.set_footer(text="FrostSTORE™ — Professional & Secure Boosting")
    await ctx.send(embed=embed)

@bot.command(name='setup_ranked')
@commands.has_permissions(administrator=True)
async def setup_ranked(ctx):
    embed = discord.Embed(
        title="<:mythicrank:123456789> Ranked Boost",
        description="Boost your ranked tier from Diamond all the way up to Pro.\n\n⭐ Fast & professional boosters\n⭐ Secure handling\n⭐ Best prices on market",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Powered by FrostSTORE™")
    await ctx.send(embed=embed, view=CatalogButtonView("Ranked Boost"))

@bot.command(name='setup_prestige')
@commands.has_permissions(administrator=True)
async def setup_prestige(ctx):
    embed = discord.Embed(
        title="<:prestige1:123456789> Prestige Service",
        description="Prestige your brawlers from Prestige I all the way up to Prestige III.\n\n⭐ Priced per brawler\n⭐ Any number of brawlers\n⭐ Fast & reliable service",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Powered by FrostSTORE™")
    await ctx.send(embed=embed, view=CatalogButtonView("Prestige"))

@bot.command(name='setup_winstreak')
@commands.has_permissions(administrator=True)
async def setup_winstreak(ctx):
    embed = discord.Embed(
        title="⚡ Winstreak Service",
        description="Unstoppable winstreaks handled by top players.\n\n⭐ Fast execution\n⭐ 100% win rate guarantee",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Powered by FrostSTORE™")
    await ctx.send(embed=embed, view=CatalogButtonView("Winstreak"))

@bot.command(name='setup_trophy')
@commands.has_permissions(administrator=True)
async def setup_trophy(ctx):
    embed = discord.Embed(
        title="🏆 Trophy Bulk Service",
        description="Bulk trophy pushes for your brawlers.\n\n⭐ Rank 30 / Rank 35 pushes\n⭐ Safe & manual play",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Powered by FrostSTORE™")
    await ctx.send(embed=embed, view=CatalogButtonView("Trophy Bulk"))

@bot.command(name='setup_matcherino')
@commands.has_permissions(administrator=True)
async def setup_matcherino(ctx):
    embed = discord.Embed(
        title="🎮 Matcherino Support",
        description="Support tournaments and get special services via Matcherino.",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Powered by FrostSTORE™")
    await ctx.send(embed=embed, view=CatalogButtonView("Matcherino"))

# --- RUN BOT ---
keep_alive()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
