import os
import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
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
MATCHERINO_STOCK = 5  # Výchozí skladová zásoba pro Matcherino

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('FrostSTORE Bot je plně spuštěný a připravený!')

# --- AUTOMATICKÉ PŘIDĚLENÍ ROLE ZA SERVER BOOST ---
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.premium_since != after.premium_since and after.premium_since is not None:
        role = discord.utils.get(after.guild.roles, name="Trusted Booster")
        if role and role not in after.roles:
            await after.add_roles(role)

# --- ŠABLONY CENÍKŮ S TVÝMI DOPLNĚNÝMI EMOJI ---
def get_service_embed_with_image(service_type: str):
    image_url = "ZDE_VLOZ_ODKAZ_NA_OBRAZEK"  # Sem vlož URL obrázku (např. z Discordu)
    
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
        desc = "⚡ **WINSTREAK SERVICE** ⚡\nZadej požadovaný winstreak (číslo) a platební metodu."
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


# --- FORMULÁŘE PRO OBJEDNÁVKY ---

class RankedTrophyOrderModal(Modal):
    def __init__(self, service_type: str):
        super().__init__(title=f"FrostSTORE — {service_type}")
        self.service_type = service_type

        self.current_stat = TextInput(label="Current Rank / Trophies", placeholder="např. Diamond 1 nebo 8000 trophies", required=True)
        self.goal_stat = TextInput(label="Goal Rank / Trophies", placeholder="např. Mythic 1 nebo 9000 trophies", required=True)
        self.p11_brawlers = TextInput(label="Počet P11 Brawlerů", placeholder="např. 15", required=True)
        self.payment_method = TextInput(label="Payment (applepay / paypal / bank)", placeholder="applepay", required=True)

        self.add_item(self.current_stat)
        self.add_item(self.goal_stat)
        self.add_item(self.p11_brawlers)
        self.add_item(self.payment_method)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            p11_count = int(self.p11_brawlers.value)
        except ValueError:
            await interaction.response.send_message("❌ Počet P11 brawlerů musí být platné číslo!", ephemeral=True)
            return

        if self.service_type == "Ranked Boost" and p11_count < 9:
            await interaction.response.send_message("❌ S méně než 9 brawlery na Power 11 nelze Ranked boost objednat.", ephemeral=True)
            return

        surcharge_text = "+0% (Základní cena)"
        if self.service_type == "Ranked Boost":
            if 9 <= p11_count <= 20:
                surcharge_text = "+50% k ceně"
            elif 21 <= p11_count <= 35:
                surcharge_text = "+25% k ceně"

        pm = self.payment_method.value.lower()
        if "apple" in pm:
            pay_name = "<:applepay:1556991495678984313> Apple Pay"
        elif "paypal" in pm:
            pay_name = "<:paypal:1556991529896247427> PayPal"
        else:
            pay_name = "<:banktransfer:1557079953101553684> Bank Transfer"

        embed = discord.Embed(title="🔔 New Order Pending Approval", description=f"Client: {interaction.user.mention}\nService: **{self.service_type}**", color=discord.Color.gold())
        embed.add_field(name="Current", value=self.current_stat.value, inline=True)
        embed.add_field(name="Goal", value=self.goal_stat.value, inline=True)
        embed.add_field(name="P11 Brawlers", value=str(p11_count), inline=False)
        embed.add_field(name="Příplatek / Pravidlo", value=surcharge_text, inline=False)
        embed.add_field(name="Payment", value=pay_name, inline=False)

        view = OwnerApprovalView(
            client=interaction.user,
            service_type=self.service_type,
            route=f"{self.current_stat.value} ➔ {self.goal_stat.value}",
            payment=pay_name,
            extra_info=f"P11: {p11_count} ({surcharge_text})"
        )
        await interaction.response.send_message("✅ Objednávka byla odeslána ke schválení majiteli!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)


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


class MatcherinoOrderModal(Modal):
    def __init__(self):
        super().__init__(title="FrostSTORE — Matcherino")
        self.payment_method = TextInput(label="Payment (applepay / paypal / bank)", placeholder="applepay", required=True)
        self.add_item(self.payment_method)

    async def on_submit(self, interaction: discord.Interaction):
        global MATCHERINO_STOCK
        if MATCHERINO_STOCK <= 0:
            await interaction.response.send_message("❌ **Omlouváme se, ale momentálně není nic na sklade!**", ephemeral=True)
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


# --- SCHVALOVÁNÍ PLATBY MAJITELEM A VYTVÁŘENÍ TICKETU ---
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


# --- OVLÁDÁNÍ V TICKETU PRO STAFF ---
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


# --- TLAČÍTKO V KATALOGU ---
class CatalogButtonView(View):
    def __init__(self, service_name: str):
        super().__init__(timeout=None)
        self.service_name = service_name

    @discord.ui.button(label="Order Now", style=discord.ButtonStyle.primary, emoji="🛒")
    async def catalog_button(self, interaction: discord.Interaction, button: Button):
        if self.service_name in ["Ranked Boost", "Trophy Bulk", "Prestige"]:
            await interaction.response.send_modal(RankedTrophyOrderModal(self.service_name))
        elif self.service_name == "Winstreak":
            await interaction.response.send_modal(WinstreakOrderModal())
        elif self.service_name == "Matcherino":
            await interaction.response.send_modal(MatcherinoOrderModal())
        else:
            await interaction.response.send_modal(RankedTrophyOrderModal(self.service_name))


# --- PŘÍKAZY PRO VYTVOŘENÍ KATALOGŮ A SEKCÍ ---

@bot.command(name='setup_ranked')
@commands.has_permissions(administrator=True)
async def setup_ranked(ctx):
    await ctx.send(embed=get_service_embed_with_image("Ranked Boost"), view=CatalogButtonView("Ranked Boost"))

@bot.command(name='setup_trophy')
@commands.has_permissions(administrator=True)
async def setup_trophy(ctx: commands.Context):
    await ctx.send(embed=get_service_embed_with_image("Trophy Bulk"), view=CatalogButtonView("Trophy Bulk"))

@bot.command(name='setup_winstreak')
@commands.has_permissions(administrator=True)
async def setup_winstreak(ctx: commands.Context):
    await ctx.send(embed=get_service_embed_with_image("Winstreak"), view=CatalogButtonView("Winstreak"))

@bot.command(name='setup_matcherino')
@commands.has_permissions(administrator=True)
async def setup_matcherino(ctx: commands.Context):
    await ctx.send(embed=get_service_embed_with_image("Matcherino"), view=CatalogButtonView("Matcherino"))

@bot.command(name='setup_prestige')
@commands.has_permissions(administrator=True)
async def setup_prestige(ctx: commands.Context):
    await ctx.send(embed=get_service_embed_with_image("Prestige"), view=CatalogButtonView("Prestige"))

@bot.command(name='set_stock')
@commands.has_permissions(administrator=True)
async def set_stock(ctx, amount: int):
    global MATCHERINO_STOCK
    MATCHERINO_STOCK = amount
    await ctx.send(f"✅ Sklad Matcherino pinů byl úspěšně nastaven na: **{MATCHERINO_STOCK} ks**")

@bot.command(name='setup_faq')
@commands.has_permissions(administrator=True)
async def setup_faq(ctx: commands.Context):
    await ctx.send(embed=discord.Embed(title="❓ FAQ", description="Často kladené otázky...", color=discord.Color.purple()))

@bot.command(name='setup_announcements')
@commands.has_permissions(administrator=True)
async def setup_announcements(ctx: commands.Context):
    await ctx.send(embed=discord.Embed(title="📢 Announcements", description="Novinky...", color=discord.Color.purple()))

@bot.command(name='setup_payments')
@commands.has_permissions(administrator=True)
async def setup_payments(ctx: commands.Context):
    await ctx.send(embed=discord.Embed(title="💳 Payments", description="Přijímáme tyto platební metody:\n<:applepay:1556991495678984313> Apple Pay\n<:paypal:1556991529896247427> PayPal\n<:banktransfer:1557079953101553684> Bank Transfer", color=discord.Color.purple()))

@bot.command(name='setup_support')
@commands.has_permissions(administrator=True)
async def setup_support(ctx: commands.Context):
    await ctx.send(embed=discord.Embed(title="❓ Support", description="Otevři ticket pro podporu.", color=discord.Color.purple()))

@bot.command(name='setup_rules')
@commands.has_permissions(administrator=True)
async def setup_rules(ctx: commands.Context):
    await ctx.send(embed=discord.Embed(title="📁 Rules", description="Pravidla pro boostery...", color=discord.Color.red()))

@bot.command(name='setup_earnings')
@commands.has_permissions(administrator=True)
async def setup_earnings(ctx: commands.Context):
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
async def setup_become_booster(ctx: commands.Context):
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
