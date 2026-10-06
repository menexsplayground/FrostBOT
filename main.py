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

# --- GLOBÁLNÍ PROMĚNNÉ ---
MONTHLY_EARNINGS = 0.0
TODAY_EARNINGS = 0.0
ACTIVE_ORDERS_DATA = []
MATCHERINO_STOCK = 5

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('FrostSTORE Bot je plně spuštěný a připravený!')

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.premium_since != after.premium_since and after.premium_since is not None:
        role = discord.utils.get(after.guild.roles, name="Trusted Booster")
        if role and role not in after.roles:
            await after.add_roles(role)

# --- ŠABLONY CENÍKŮ ---
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
            "• **0–8 P11 Brawlerů:** ❌ Nelze objednat!\n"
            "• **9–20 P11 Brawlerů:** +50% k ceně\n"
            "• **21–35 P11 Brawlerů:** +25% k ceně\n"
            "• **35–50 P11 Brawlerů:** Základní cena (+0%)\n\n"
            "Ranky: <:bronzerank:1556988812046114826> <:silverrank:155698887283400724> <:goldrank:1556988947031400588> <:diamondrank:1556988995970535544> <:mythicrank:1556990569689911366> <:legendaryrank:1556989092577681470> <:prorank:1556989154900836403> <:mastersrank:1556990538677223485>"
        )
        color = discord.Color.blue()
    elif service_type == "Winstreak":
        desc = "⚡ **WINSTREAK SERVICE** ⚡\nVyber požadovaný winstreak a platební metodu kliknutím níže."
        color = discord.Color.orange()
    elif service_type == "Trophy Bulk":
        desc = "🏆 **TROPHY BULK SERVICE** 🏆\nHromadné navyšování trofejí s ohledem na počet P11 brawlerů."
        color = discord.Color.gold()
    elif service_type == "Matcherino":
        desc = f"🎟️ **MATCHERINO PINS / CODES** 🎟️\nAktuálně skladem: **{MATCHERINO_STOCK} ks**"
        color = discord.Color.red()
    else:
        desc = f"Professional boosting services for {service_type}."
        color = discord.Color.purple()

    embed = discord.Embed(title=f"{service_type} Service", description=desc, color=color)
    if image_url != "ZDE_VLOZ_ODKAZ_NA_OBRAZEK":
        embed.set_image(url=image_url)
    embed.set_footer(text="Powered by FrostSTORE™")
    return embed


# --- KLIKACÍ INTERAKTIVNÍ MENU PRO OBJEDNÁVKY ---

class RankedTrophySelectView(View):
    def __init__(self, service_type: str):
        super().__init__(timeout=None)
        self.service_type = service_type
        
        # Přidáme tlačítko pro spustění interaktivního výběru
        self.add_item(RankedOrderStartButton(service_type))

class RankedOrderStartButton(Button):
    def __init__(self, service_type: str):
        super().__init__(label="Order Now (Click to Select)", style=discord.ButtonStyle.primary, emoji="🛒")
        self.service_type = service_type

    async def callback(self, interaction: discord.Interaction):
        view = InteractiveOrderDropdownView(self.service_type)
        await interaction.response.send_message("👇 **Vyber parametry své objednávky přes rozbalovací menu níže:**", view=view, ephemeral=True)


class InteractiveOrderDropdownView(View):
    def __init__(self, service_type: str):
        super().__init__(timeout=180)
        self.service_type = service_type
        self.current_rank = None
        self.goal_rank = None
        self.p11_count = None
        self.payment = None

        # Přidáme select menu pro Current Rank
        self.add_item(CurrentRankSelect())
        # Přidáme select menu pro Goal Rank
        self.add_item(GoalRankSelect())
        # Přidáme select menu pro P11 brawlery
        self.add_item(P11CountSelect())
        # Přidáme select menu pro Platební metodu
        self.add_item(PaymentMethodSelect())

    @discord.ui.button(label="Odeslat objednávku", style=discord.ButtonStyle.success, emoji="✅", row=4)
    async def submit_order(self, interaction: discord.Interaction, button: Button):
        if not all([self.current_rank, self.goal_rank, self.p11_count, self.payment]):
            await interaction.response.send_message("❌ Nejsou vybrány všechny položky! Prosím vyberte všechny možnosti v menu.", ephemeral=True)
            return

        try:
            p11_val = int(self.p11_count)
        except ValueError:
            p11_val = 15

        if self.service_type == "Ranked Boost" and p11_val < 9:
            await interaction.response.send_message("❌ S méně než 9 brawlery na Power 11 nelze Ranked boost objednat.", ephemeral=True)
            return

        surcharge_text = "+0% (Základní cena)"
        if self.service_type == "Ranked Boost":
            if 9 <= p11_val <= 20:
                surcharge_text = "+50% k ceně"
            elif 21 <= p11_val <= 35:
                surcharge_text = "+25% k ceně"

        embed = discord.Embed(title="🔔 New Order Pending Approval", description=f"Client: {interaction.user.mention}\nService: **{self.service_type}**", color=discord.Color.gold())
        embed.add_field(name="Current", value=self.current_rank, inline=True)
        embed.add_field(name="Goal", value=self.goal_rank, inline=True)
        embed.add_field(name="P11 Brawlers", value=str(p11_val), inline=False)
        embed.add_field(name="Příplatek / Pravidlo", value=surcharge_text, inline=False)
        embed.add_field(name="Payment", value=self.payment, inline=False)

        view = OwnerApprovalView(
            client=interaction.user,
            service_type=self.service_type,
            route=f"{self.current_rank} ➔ {self.goal_rank}",
            payment=self.payment,
            extra_info=f"P11: {p11_val} ({surcharge_text})"
        )
        await interaction.response.edit_message(content="✅ Objednávka byla úspěšně odeslána ke schválení majiteli!", view=None)
        await interaction.channel.send(embed=embed, view=view)


class CurrentRankSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bronze", emoji="<:bronzerank:1556988812046114826>"),
            discord.SelectOption(label="Silver", emoji="<:silverrank:155698887283400724>"),
            discord.SelectOption(label="Gold", emoji="<:goldrank:1556988947031400588>"),
            discord.SelectOption(label="Diamond", emoji="<:diamondrank:1556988995970535544>"),
            discord.SelectOption(label="Mythic", emoji="<:mythicrank:1556990569689911366>"),
            discord.SelectOption(label="Legendary", emoji="<:legendaryrank:1556989092577681470>"),
            discord.SelectOption(label="Masters", emoji="<:mastersrank:1556990538677223485>"),
        ]
        super().__init__(placeholder="1️⃣ Vyber aktuální rank / stav...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.current_rank = self.values[0]
        await interaction.response.defer()


class GoalRankSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Silver", emoji="<:silverrank:155698887283400724>"),
            discord.SelectOption(label="Gold", emoji="<:goldrank:1556988947031400588>"),
            discord.SelectOption(label="Diamond", emoji="<:diamondrank:1556988995970535544>"),
            discord.SelectOption(label="Mythic", emoji="<:mythicrank:1556990569689911366>"),
            discord.SelectOption(label="Legendary", emoji="<:legendaryrank:1556989092577681470>"),
            discord.SelectOption(label="Masters", emoji="<:mastersrank:1556990538677223485>"),
            discord.SelectOption(label="Pro Rank", emoji="<:prorank:1556989154900836403>"),
        ]
        super().__init__(placeholder="2️⃣ Vyber cílový rank...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.goal_rank = self.values[0]
        await interaction.response.defer()


class P11CountSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="9-20 P11 Brawlerů (+50%)", value="15"),
            discord.SelectOption(label="21-35 P11 Brawlerů (+25%)", value="25"),
            discord.SelectOption(label="35-50 P11 Brawlerů (Základ)", value="40"),
        ]
        super().__init__(placeholder="3️⃣ Vyber počet P11 brawlerů...", options=options, row=2)

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
        super().__init__(placeholder="4️⃣ Vyber platební metodu...", options=options, row=3)

    async def callback(self, interaction: discord.Interaction):
        self.view.payment = self.values[0]
        await interaction.response.defer()


# --- OSTATNÍ SLUŽBY (Winstreak / Matcherino) ---
class WinstreakSelectView(View):
    @discord.ui.button(label="Objednat Winstreak", style=discord.ButtonStyle.primary, emoji="⚡")
    async def winstreak_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(WinstreakOrderModal())

class WinstreakOrderModal(Modal):
    def __init__(self):
        super().__init__(title="FrostSTORE — Winstreak")
        self.target_streak = TextInput(label="Zadání / Požadovaný Winstreak", placeholder="např. 15 winů v řadě", required=True)
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
        embed.add_field(name="Zadání / Cíl", value=self.target_streak.value, inline=False)
        embed.add_field(name="Payment", value=pay_name, inline=False)

        view = OwnerApprovalView(
            client=interaction.user,
            service_type="Winstreak",
            route=f"Streak: {self.target_streak.value}",
            payment=pay_name,
            extra_info="Winstreak objednávka"
        )
        await interaction.response.send_message("✅ Objednávka byla odeslána ke schválení majiteli!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)


class MatcherinoSelectView(View):
    @discord.ui.button(label="Objednat Matcherino Pin", style=discord.ButtonStyle.danger, emoji="🎟️")
    async def matcherino_btn(self, interaction: discord.Interaction, button: Button):
        global MATCHERINO_STOCK
        if MATCHERINO_STOCK <= 0:
            await interaction.response.send_message("❌ **Omlouváme se, ale momentálně není nic na skladě!**", ephemeral=True)
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
            await interaction.response.send_message("❌ Sklad je prázdný!", ephemeral=True)
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
            extra_info="Matcherino skladový produkt"
        )
        await interaction.response.send_message("✅ Objednávka byla odeslána ke schválení majiteli!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)


# --- SCHVALOVÁNÍ PLATBY A TICKETU ---
class OwnerApprovalView(View):
    def __init__(self, client, service_type, route, payment, extra_info):
        super().__init__(timeout=None)
        self.client = client
        self.service_type = service_type
        self.route = route
        self.payment = payment
        self.extra_info = extra_info

    @discord.ui.button(label="Confirm Payment & Create Ticket", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_payment(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.client: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        channel_count = len(guild.text_channels)
        ticket_channel = await guild.create_text_channel(name=f"order-{self.client.name}-{channel_count}".lower(), overwrites=overwrites)

        embed = discord.Embed(
            title=f"🚀 Secure Order Ticket — {self.service_type}",
            description=f"Client: {self.client.mention}\nProgress: 🛌 0% (Waiting for booster)\n\n*Použij tlačítka níže pro správu.*",
            color=discord.Color.purple()
        )
        embed.add_field(name="Detail / Route", value=self.route, inline=False)
        embed.add_field(name="Info", value=self.extra_info, inline=False)
        embed.add_field(name="Payment", value=self.payment, inline=False)

        staff_view = StaffOrderControlView(client_name=self.client.name, service_short=self.service_type)
        await ticket_channel.send(embed=embed, view=staff_view)

        ACTIVE_ORDERS_DATA.append({
            "client": self.client.name,
            "route": self.route,
            "price": "35€",
            "status_emoji": "🛌",
            "percent": 0
        })

        avail_channel = discord.utils.get(guild.text_channels, name="avalabile-orders")
        if avail_channel:
            avail_embed = discord.Embed(
                title="✅ New Available Boost Order!",
                description=f"Service: **{self.service_type}**\nDetail: `{self.route}`\nClient: {self.client.name}",
                color=discord.Color.green()
            )
            await avail_channel.send(embed=avail_embed)

        await interaction.message.delete()
        await interaction.response.send_message(f"💳 Platba potvrzena! Byl vytvořen nový ticket: {ticket_channel.mention}", ephemeral=True)


class StaffOrderControlView(View):
    def __init__(self, client_name, service_short):
        super().__init__(timeout=None)
        self.client_name = client_name
        self.service_short = service_short

    @discord.ui.button(label="Booster Online (🟢)", style=discord.ButtonStyle.secondary)
    async def booster_online(self, interaction: discord.Interaction, button: Button):
        for o in ACTIVE_ORDERS_DATA:
            if o["client"] == self.client_name:
                o["status_emoji"] = "🟢"
        await interaction.response.send_message("🟢 Booster je aktivní na této objednávce!", ephemeral=True)

    @discord.ui.button(label="Close & Review", style=discord.ButtonStyle.danger, emoji="⭐")
    async def close_order(self, interaction: discord.Interaction, button: Button):
        global MONTHLY_EARNINGS, TODAY_EARNINGS, ACTIVE_ORDERS_DATA
        MONTHLY_EARNINGS += 35.0
        TODAY_EARNINGS += 35.0
        ACTIVE_ORDERS_DATA = [o for o in ACTIVE_ORDERS_DATA if o["client"] != self.client_name]

        guild = interaction.guild
        review_channel = discord.utils.get(guild.text_channels, name="review")
        if review_channel:
            await review_channel.send(embed=discord.Embed(title="⭐ Review Request", description=f"Klient **{self.client_name}** dokončil objednávku!", color=discord.Color.gold()))

        await interaction.channel.send("⭐ Objednávka dokončena, archivuji kanál...")
        await interaction.message.delete()


# --- PŘÍKAZY PRO VYTVOŘENÍ KATALOGŮ ---

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
    await ctx.send(f"✅ Sklad Matcherino pinů byl úspěšně nastaven na: **{MATCHERINO_STOCK} ks**")

@bot.command(name='setup_faq')
@commands.has_permissions(administrator=True)
async def setup_faq(ctx):
    await ctx.send(embed=discord.Embed(title="❓ FAQ", description="Často kladené otázky...", color=discord.Color.purple()))

@bot.command(name='setup_announcements')
@commands.has_permissions(administrator=True)
async def setup_announcements(ctx):
    await ctx.send(embed=discord.Embed(title="📢 Announcements", description="Novinky...", color=discord.Color.purple()))

@bot.command(name='setup_payments')
@commands.has_permissions(administrator=True)
async def setup_payments(ctx):
    await ctx.send(embed=discord.Embed(title="💳 Payments", description="Přijímáme tyto platební metody:\n<:applepay:1556991495678984313> Apple Pay\n<:paypal:1556991529896247427> PayPal\n<:banktransfer:1557079953101553684> Bank Transfer", color=discord.Color.purple()))

@bot.command(name='setup_support')
@commands.has_permissions(administrator=True)
async def setup_support(ctx):
    await ctx.send(embed=discord.Embed(title="❓ Support", description="Otevři ticket pro podporu.", color=discord.Color.purple()))

@bot.command(name='setup_rules')
@commands.has_permissions(administrator=True)
async def setup_rules(ctx):
    await ctx.send(embed=discord.Embed(title="📁 Rules", description="Pravidla pro boostery...", color=discord.Color.red()))

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
            await interaction.response.send_message("Náborový formulář do týmu boosterů...", ephemeral=True)
    await ctx.send(embed=discord.Embed(title="⭐ Become a Booster", description="Klikni pro přihlášení do týmu boosterů.", color=discord.Color.gold()), view=view)

# --- SPUŠTĚNÍ BOTA ---
keep_alive()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
