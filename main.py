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
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- GLOBAL VARIABLES ---
MONTHLY_EARNINGS = 0.0
TODAY_EARNINGS = 0.0
ACTIVE_ORDERS_DATA = []
MATCHERINO_STOCK = 5

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('FrostSTORE Bot is fully online and ready!')

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.premium_since != after.premium_since and after.premium_since is not None:
        role = discord.utils.get(after.guild.roles, name="Trusted Booster")
        if role and role not in after.roles:
            await after.add_roles(role)

# --- SERVICE EMBED TEMPLATES ---
def get_service_embed_with_image(service_type: str):
    image_url = "ZDE_VLOZ_ODKAZ_NA_OBRAZEK"
    
    if service_type == "Prestige":
        desc = (
            "Prestige your brawlers from <:prestige1:1556990921583886437> Prestige I all the way up to <:prestige3:1556990963254173816> Prestige III.\n\n"
            "⭐ Priced per brawler\n"
            "⭐ Any number of brawlers\n"
            "⭐ Fast & reliable service"
        )
        color = discord.Color.purple()
    elif service_type == "Ranked Boost":
        desc = (
            "💎 **RANKED BOOST PRICING & P11 RULES** 💎\n\n"
            "• **0–8 P11 Brawlers:** ❌ Cannot be ordered!\n"
            "• **9–20 P11 Brawlers:** +50% price surcharge\n"
            "• **21–35 P11 Brawlers:** +25% price surcharge\n"
            "• **35–50 P11 Brawlers:** Base price (+0%)\n\n"
            "Ranks: <:bronzerank:1556988812046114826> <:silverrank:155698887283400724> <:goldrank:1556988947031400588> <:diamondrank:1556988995970535544> <:mythicrank:1556990569689911366> <:legendaryrank:1556989092577681470> <:prorank:1556989154900836403> <:mastersrank:1556990538677223485>"
        )
        color = discord.Color.blue()
    elif service_type == "Winstreak":
        desc = "⚡ **WINSTREAK SERVICE** ⚡\nSelect your desired winstreak and payment method below."
        color = discord.Color.orange()
    elif service_type == "Trophy Bulk":
        desc = "🏆 **TROPHY BULK SERVICE** 🏆\nBulk trophy boosting based on your P11 brawler count."
        color = discord.Color.gold()
    elif service_type == "Matcherino":
        desc = f"🎟️ **MATCHERINO PINS / CODES** 🎟️\nCurrently in stock: **{MATCHERINO_STOCK} pcs**"
        color = discord.Color.red()
    else:
        desc = f"Professional boosting services for {service_type}."
        color = discord.Color.purple()

    embed = discord.Embed(title=f"{service_type} Service", description=desc, color=color)
    if image_url != "ZDE_VLOZ_ODKAZ_NA_OBRAZEK":
        embed.set_image(url=image_url)
    embed.set_footer(text="Powered by FrostSTORE™")
    return embed


# --- INTERACTIVE DROPDOWN ORDER VIEWS ---

class RankedTrophySelectView(View):
    def __init__(self, service_type: str):
        super().__init__(timeout=None)
        self.service_type = service_type
        self.add_item(RankedOrderStartButton(service_type))

class RankedOrderStartButton(Button):
    def __init__(self, service_type: str):
        super().__init__(label="Order Now (Click to Select)", style=discord.ButtonStyle.primary, emoji="🛒")
        self.service_type = service_type

    async def callback(self, interaction: discord.Interaction):
        view = InteractiveOrderDropdownView(self.service_type)
        await interaction.response.send_message("👇 **Select your order options using the dropdowns below:**", view=view, ephemeral=True)


class InteractiveOrderDropdownView(View):
    def __init__(self, service_type: str):
        super().__init__(timeout=180)
        self.service_type = service_type
        self.current_rank = None
        self.goal_rank = None
        self.p11_count = None
        self.payment = None

        self.add_item(CurrentRankSelect())
        self.add_item(GoalRankSelect())
        self.add_item(P11CountSelect())
        self.add_item(PaymentMethodSelect())

    @discord.ui.button(label="Submit Order", style=discord.ButtonStyle.success, emoji="✅", row=4)
    async def submit_order(self, interaction: discord.Interaction, button: Button):
        if not all([self.current_rank, self.goal_rank, self.p11_count, self.payment]):
            await interaction.response.send_message("❌ Please select all options in the dropdown menus before submitting!", ephemeral=True)
            return

        try:
            p11_val = int(self.p11_count)
        except ValueError:
            p11_val = 15

        if self.service_type == "Ranked Boost" and p11_val < 9:
            await interaction.response.send_message("❌ You need at least 9 P11 brawlers to order a Ranked boost.", ephemeral=True)
            return

        base_price = 25.0
        surcharge_text = "+0% (Base Price)"
        if self.service_type == "Ranked Boost":
            if 9 <= p11_val <= 20:
                base_price *= 1.50
                surcharge_text = "+50% Surcharge"
            elif 21 <= p11_val <= 35:
                base_price *= 1.25
                surcharge_text = "+25% Surcharge"

        embed = discord.Embed(title="🔔 New Order Pending Approval", description=f"Client: {interaction.user.mention}\nService: **{self.service_type}**", color=discord.Color.gold())
        embed.add_field(name="Current", value=self.current_rank, inline=True)
        embed.add_field(name="Goal", value=self.goal_rank, inline=True)
        embed.add_field(name="P11 Brawlers", value=str(p11_val), inline=False)
        embed.add_field(name="Rule / Surcharge", value=surcharge_text, inline=False)
        embed.add_field(name="Calculated Price", value=f"{base_price:.2f}€", inline=False)
        embed.add_field(name="Payment", value=self.payment, inline=False)

        view = OwnerApprovalView(
            client=interaction.user,
            service_type=self.service_type,
            route=f"{self.current_rank} ➔ {self.goal_rank}",
            payment=self.payment,
            price_val=base_price,
            extra_info=f"P11: {p11_val} ({surcharge_text})"
        )
        await interaction.response.edit_message(content="✅ Your order has been successfully sent for owner approval!", view=None)
        await interaction.channel.send(embed=embed, view=view)


class CurrentRankSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bronze I", emoji="<:bronzerank:1556988812046114826>"),
            discord.SelectOption(label="Bronze II", emoji="<:bronzerank:1556988812046114826>"),
            discord.SelectOption(label="Bronze III", emoji="<:bronzerank:1556988812046114826>"),
            discord.SelectOption(label="Silver I", emoji="<:silverrank:155698887283400724>"),
            discord.SelectOption(label="Silver II", emoji="<:silverrank:155698887283400724>"),
            discord.SelectOption(label="Silver III", emoji="<:silverrank:155698887283400724>"),
            discord.SelectOption(label="Gold I", emoji="<:goldrank:1556988947031400588>"),
            discord.SelectOption(label="Diamond I", emoji="<:diamondrank:1556988995970535544>"),
            discord.SelectOption(label="Mythic I", emoji="<:mythicrank:1556990569689911366>"),
            discord.SelectOption(label="Legendary I", emoji="<:legendaryrank:1556989092577681470>"),
            discord.SelectOption(label="Masters", emoji="<:mastersrank:1556990538677223485>"),
        ]
        super().__init__(placeholder="Select your CURRENT rank...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.current_rank = self.values[0]
        await interaction.response.defer()


class GoalRankSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bronze II", emoji="<:bronzerank:1556988812046114826>"),
            discord.SelectOption(label="Silver I", emoji="<:silverrank:155698887283400724>"),
            discord.SelectOption(label="Gold I", emoji="<:goldrank:1556988947031400588>"),
            discord.SelectOption(label="Diamond I", emoji="<:diamondrank:1556988995970535544>"),
            discord.SelectOption(label="Mythic I", emoji="<:mythicrank:1556990569689911366>"),
            discord.SelectOption(label="Legendary I", emoji="<:legendaryrank:1556989092577681470>"),
            discord.SelectOption(label="Masters", emoji="<:mastersrank:1556990538677223485>"),
            discord.SelectOption(label="Pro Rank", emoji="<:prorank:1556989154900836403>"),
        ]
        super().__init__(placeholder="Select your DESIRED rank...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.goal_rank = self.values[0]
        await interaction.response.defer()


class P11CountSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="9-20 P11 Brawlers (+50%)", value="15"),
            discord.SelectOption(label="21-35 P11 Brawlers (+25%)", value="25"),
            discord.SelectOption(label="35-50 P11 Brawlers (Base Price)", value="40"),
        ]
        super().__init__(placeholder="Select number of P11 Brawlers...", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        self.view.p11_count = self.values[0]
        await interaction.response.defer()


class PaymentMethodSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Apple Pay", emoji="<:applepay:1556991495678984313>", value="<:applepay:1556991495678984313> Apple Pay"),
            discord.SelectOption(label="PayPal", emoji="<:paypal:1556991529896247427>", value="<:paypal:1556991529896247427> PayPal"),
            discord.SelectOption(label="Bank Transfer", emoji="<:banktransfer:1557079953101553684>", value="<:banktransfer:1557079953101553684> Bank Transfer"),
        ]
        super().__init__(placeholder="Select payment method...", options=options, row=3)

    async def callback(self, interaction: discord.Interaction):
        self.view.payment = self.values[0]
        await interaction.response.defer()


# --- WINSTREAK & MATCHERINO ---
class WinstreakSelectView(View):
    @discord.ui.button(label="Order Winstreak", style=discord.ButtonStyle.primary, emoji="⚡")
    async def winstreak_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(WinstreakOrderModal())

class WinstreakOrderModal(Modal):
    def __init__(self):
        super().__init__(title="FrostSTORE — Winstreak")
        self.target_streak = TextInput(label="Desired Winstreak", placeholder="e.g. 15 wins in a row", required=True)
        self.payment_method = TextInput(label="Payment (applepay / paypal / bank)", placeholder="paypal", required=True)
        self.add_item(self.target_streak)
        self.add_item(self.payment_method)

    async def on_submit(self, interaction: discord.Interaction):
        pm = self.payment_method.value.lower()
        if "apple" in pm:
            pay_name = "<:applepay:1556991495678984313> Apple Pay"
        elif "paypal" in pm:
            pay_name = "<:paypal:1556991529896247427> PayPal"
        else:
            pay_name = "<:banktransfer:1557079953101553684> Bank Transfer"

        embed = discord.Embed(title="🔔 New Order Pending Approval", description=f"Client: {interaction.user.mention}\nService: **Winstreak**", color=discord.Color.gold())
        embed.add_field(name="Target", value=self.target_streak.value, inline=False)
        embed.add_field(name="Payment", value=pay_name, inline=False)

        view = OwnerApprovalView(
            client=interaction.user,
            service_type="Winstreak",
            route=f"Streak: {self.target_streak.value}",
            payment=pay_name,
            price_val=20.0,
            extra_info="Winstreak order"
        )
        await interaction.response.send_message("✅ Order sent for approval!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)


class MatcherinoSelectView(View):
    @discord.ui.button(label="Order Matcherino Pin", style=discord.ButtonStyle.danger, emoji="🎟️")
    async def matcherino_btn(self, interaction: discord.Interaction, button: Button):
        global MATCHERINO_STOCK
        if MATCHERINO_STOCK <= 0:
            await interaction.response.send_message("❌ **Sorry, currently out of stock!**", ephemeral=True)
            return
        await interaction.response.send_modal(MatcherinoOrderModal())

class MatcherinoOrderModal(Modal):
    def __init__(self):
        super().__init__(title="FrostSTORE — Matcherino")
        self.payment_method = TextInput(label="Payment (applepay / paypal / bank)", placeholder="applepay", required=True)
        self.add_item(self.payment_method)

    async def on_submit(self, interaction: discord.Interaction):
        global MATCHERINO_STOCK
        if MATCHERINO_STOCK <= 0:
            await interaction.response.send_message("❌ Stock is empty!", ephemeral=True)
            return

        pm = self.payment_method.value.lower()
        if "apple" in pm:
            pay_name = "<:applepay:1556991495678984313> Apple Pay"
        elif "paypal" in pm:
            pay_name = "<:paypal:1556991529896247427> PayPal"
        else:
            pay_name = "<:banktransfer:1557079953101553684> Bank Transfer"

        embed = discord.Embed(title="🔔 New Matcherino Order Pending", description=f"Client: {interaction.user.mention}\nService: **Matcherino**", color=discord.Color.gold())
        embed.add_field(name="Payment", value=pay_name, inline=False)

        view = OwnerApprovalView(
            client=interaction.user,
            service_type="Matcherino",
            route="Matcherino Pin/Code",
            payment=pay_name,
            price_val=10.0,
            extra_info="Matcherino stock product"
        )
        await interaction.response.send_message("✅ Order sent for approval!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)


# --- OWNER APPROVAL & TICKETS ---
class OwnerApprovalView(View):
    def __init__(self, client, service_type, route, payment, price_val, extra_info):
        super().__init__(timeout=None)
        self.client = client
        self.service_type = service_type
        self.route = route
        self.payment = payment
        self.price_val = price_val
        self.extra_info = extra_info

    @discord.ui.button(label="Confirm Payment & Create Ticket", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_payment(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.client: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        channel_count = len(guild.text_channels)
        ticket_channel = await guild.create_text_channel(name=f"order-{self.client.name}-{channel_count}".lower(), overwrites=overwrites)

        embed = discord.Embed(
            title=f"🚀 Secure Order Ticket — {self.service_type}",
            description=f"Client: {self.client.mention}\nProgress: 🛌 0% (Waiting for booster)\n\n*Use buttons below for order control.*",
            color=discord.Color.purple()
        )
        embed.add_field(name="Route / Detail", value=self.route, inline=False)
        embed.add_field(name="Info", value=self.extra_info, inline=False)
        embed.add_field(name="Price", value=f"{self.price_val:.2f}€", inline=True)
        embed.add_field(name="Payment", value=self.payment, inline=True)

        staff_view = StaffOrderControlView(client_name=self.client.name, service_short=self.service_type, price_val=self.price_val)
        await ticket_channel.send(embed=embed, view=staff_view)

        ACTIVE_ORDERS_DATA.append({
            "client": self.client.name,
            "route": self.route,
            "price": f"{self.price_val:.2f}€",
            "status_emoji": "🛌",
            "percent": 0
        })

        avail_channel = discord.utils.get(guild.text_channels, name="avalabile-orders")
        if avail_channel:
            avail_embed = discord.Embed(
                title="✅ New Available Boost Order!",
                description=f"Service: **{self.service_type}**\nDetail: `{self.route}`\nPrice: **{self.price_val:.2f}€**\nClient: {self.client.name}",
                color=discord.Color.green()
            )
            await avail_channel.send(embed=avail_embed)

        await interaction.message.delete()
        await interaction.response.send_message(f"💳 Payment confirmed! Ticket created: {ticket_channel.mention}", ephemeral=True)


class StaffOrderControlView(View):
    def __init__(self, client_name, service_short, price_val):
        super().__init__(timeout=None)
        self.client_name = client_name
        self.service_short = service_short
        self.price_val = price_val

    @discord.ui.button(label="Booster Online (🟢)", style=discord.ButtonStyle.secondary)
    async def booster_online(self, interaction: discord.Interaction, button: Button):
        for o in ACTIVE_ORDERS_DATA:
            if o["client"] == self.client_name:
                o["status_emoji"] = "🟢"
        await interaction.response.send_message("🟢 Booster marked as active!", ephemeral=True)

    @discord.ui.button(label="Close & Review", style=discord.ButtonStyle.danger, emoji="⭐")
    async def close_order(self, interaction: discord.Interaction, button: Button):
        global MONTHLY_EARNINGS, TODAY_EARNINGS, ACTIVE_ORDERS_DATA
        MONTHLY_EARNINGS += self.price_val
        TODAY_EARNINGS += self.price_val
        ACTIVE_ORDERS_DATA = [o for o in ACTIVE_ORDERS_DATA if o["client"] != self.client_name]

        guild = interaction.guild
        review_channel = discord.utils.get(guild.text_channels, name="review")
        if review_channel:
            await review_channel.send(embed=discord.Embed(title="⭐ Review Request", description=f"Client **{self.client_name}** has completed their order!", color=discord.Color.gold()))

        await interaction.channel.send("⭐ Order completed, archiving channel...")
        await interaction.message.delete()


# --- SETUP COMMANDS ---

@bot.command(name='setup_order')
@commands.has_permissions(administrator=True)
async def setup_order(ctx):
    embed = discord.Embed(
        title="🛒 How to Order",
        description=(
            "1. **Choose Service**\n"
            "Head over to our **SERVICES** category (`#ranked`, `#prestige`, `#winstreak`, etc.).\n\n"
            "2. **Click & Fill Form**\n"
            "Click the **Order Now** button under your desired service. A form will pop up for you to fill in your current stats, goals, and brawlers.\n\n"
            "3. **Payment Methods**\n"
            "We accept secure payments via:\n"
            "<:applepay:1556991495678984313> **Apple Pay**\n"
            "<:paypal:1556991529896247427> **PayPal**\n"
            "<:banktransfer:1557079953101553684> **Bank Transfer**\n\n"
            "4. **Secure Ticket**\n"
            "Once the owner confirms your payment, a private secure ticket will be created automatically for your boost!"
        ),
        color=discord.Color.purple()
    )
    embed.set_footer(text="FrostSTORE™ — Professional & Secure Boosting")
    await ctx.send(embed=embed)

@bot.command(name='setup_ranked')
@commands.has_permissions(administrator=True)
async def setup_ranked(ctx):
    await ctx.send(embed=get_service_embed_with_image("Ranked Boost"), view=RankedTrophySelectView("Ranked Boost"))

@bot.command(name='setup_trophy')
@commands.has_permissions(administrator=True)
async def setup_trophy(ctx):
    await ctx.send(embed=get_service_embed_with_image("Trophy Bulk"), view=RankedTrophySelectView("Trophy Bulk"))

@bot.command(name='setup_prestige')
@commands.has_permissions(administrator=True)
async def setup_prestige(ctx):
    await ctx.send(embed=get_service_embed_with_image("Prestige"), view=RankedTrophySelectView("Prestige"))

@bot.command(name='setup_winstreak')
@commands.has_permissions(administrator=True)
async def setup_winstreak(ctx):
    await ctx.send(embed=get_service_embed_with_image("Winstreak"), view=WinstreakSelectView())

@bot.command(name='setup_matcherino')
@commands.has_permissions(administrator=True)
async def setup_matcherino(ctx):
    await ctx.send(embed=get_service_embed_with_image("Matcherino"), view=MatcherinoSelectView())

@bot.command(name='set_stock')
@commands.has_permissions(administrator=True)
async def set_stock(ctx, amount: int):
    global MATCHERINO_STOCK
    MATCHERINO_STOCK = amount
    await ctx.send(f"✅ Matcherino stock successfully updated to: **{MATCHERINO_STOCK} pcs**")

@bot.command(name='add_earnings')
@commands.has_permissions(administrator=True)
async def add_earnings(ctx, amount: float):
    global MONTHLY_EARNINGS, TODAY_EARNINGS
    MONTHLY_EARNINGS += amount
    TODAY_EARNINGS += amount
    await ctx.send(f"✅ Successfully added **{amount}€** to booster earnings!")

@bot.command(name='set_earnings')
@commands.has_permissions(administrator=True)
async def set_earnings(ctx, monthly: float, today: float):
    global MONTHLY_EARNINGS, TODAY_EARNINGS
    MONTHLY_EARNINGS = monthly
    TODAY_EARNINGS = today
    await ctx.send(f"✅ Earnings updated! Monthly: **{MONTHLY_EARNINGS}€**, Today: **{TODAY_EARNINGS}€**")

@bot.command(name='setup_faq')
@commands.has_permissions(administrator=True)
async def setup_faq(ctx):
    await ctx.send(embed=discord.Embed(title="❓ FAQ", description="Frequently asked questions...", color=discord.Color.purple()))

@bot.command(name='setup_announcements')
@commands.has_permissions(administrator=True)
async def setup_announcements(ctx):
    await ctx.send(embed=discord.Embed(title="📢 Announcements", description="Latest news...", color=discord.Color.purple()))

@bot.command(name='setup_payments')
@commands.has_permissions(administrator=True)
async def setup_payments(ctx):
    await ctx.send(embed=discord.Embed(title="💳 Payments", description="We accept:\n<:applepay:1556991495678984313> Apple Pay\n<:paypal:1556991529896247427> PayPal\n<:banktransfer:1557079953101553684> Bank Transfer", color=discord.Color.purple()))

@bot.command(name='setup_support')
@commands.has_permissions(administrator=True)
async def setup_support(ctx):
    await ctx.send(embed=discord.Embed(title="❓ Support", description="Open a ticket for support.", color=discord.Color.purple()))

@bot.command(name='setup_rules')
@commands.has_permissions(administrator=True)
async def setup_rules(ctx):
    await ctx.send(embed=discord.Embed(title="📁 Rules", description="Rules for boosters...", color=discord.Color.red()))

@bot.command(name='setup_earnings')
@commands.has_permissions(administrator=True)
async def setup_earnings(ctx):
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

@bot.command(name='setup_become_booster')
@commands.has_permissions(administrator=True)
async def setup_become_booster(ctx):
    view = View(timeout=None)
    @view.item
    class ApplyBtn(Button):
        def __init__(self):
            super().__init__(label="Apply to Become a Booster", style=discord.ButtonStyle.success)
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message("Booster application form...", ephemeral=True)
    await ctx.send(embed=discord.Embed(title="⭐ Become a Booster", description="Click to apply for the booster team.", color=discord.Color.gold()), view=view)

# --- RUN BOT ---
keep_alive()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
