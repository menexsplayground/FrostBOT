import os
import time
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

# --- DATABÁZE RANKŮ A ELO ---
RANKS = {
    "Bronze I": 0, "Bronze II": 250, "Bronze III": 500,
    "Silver I": 750, "Silver II": 1000, "Silver III": 1250,
    "Gold I": 1500, "Gold II": 2000, "Gold III": 2500,
    "Diamond I": 3000, "Diamond II": 3500, "Diamond III": 4000,
    "Mythic I": 4500, "Mythic II": 5000, "Mythic III": 5500,
    "Legendary I": 6000, "Legendary II": 6750, "Legendary III": 7500,
    "Masters I": 8250, "Masters II": 9250, "Masters III": 10250,
    "Pro": 11250
}

# Paměť aktivních zakázek (propojené tickety)
active_orders = {}
checkin_times = {}

@bot.event
async def on_ready():
    print(f"Bot {bot.user} je úspěšně spuštěn a online!")

# ==========================================
# 1. ČÁST: CHECK-IN & CHECK-OUT PRO BOOSTERY
# ==========================================

class TrophiesModal(Modal, title="Check-out: Pohárky"):
    current_trophies = TextInput(label="Aktuální pohárky", placeholder="Např. 750")

    def __init__(self, start_val, target_val, customer_channel_id):
        super().__init__()
        self.start_val = start_val
        self.target_val = target_val
        self.customer_channel_id = customer_channel_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            curr = int(self.current_trophies.value)
        except ValueError:
            await interaction.response.send_message("❌ Zadej platné číslo!", ephemeral=True)
            return

        total_needed = self.target_val - self.start_val
        progress_made = curr - self.start_val
        procento = max(0, min(100, int((progress_made / total_needed) * 100))) if total_needed > 0 else 100
        
        await update_customer_ticket(bot, self.customer_channel_id, procento, f"Pohárky: **{curr} / {self.target_val} 🏆**")
        await interaction.response.send_message(f"✅ Pokrok aktualizován na **{procento} %**!", ephemeral=True)

class RankUpdateView(View):
    def __init__(self, start_elo, target_elo, customer_channel_id):
        super().__init__(timeout=120)
        self.start_elo = start_elo
        self.target_elo = target_elo
        self.customer_channel_id = customer_channel_id

        options = [discord.SelectOption(label=rank, value=str(elo)) for rank, elo in RANKS.items() if elo >= start_elo and elo <= target_elo]
        if options:
            self.add_item(RankSelect(options, start_elo, target_elo, customer_channel_id))

class RankSelect(Select):
    def __init__(self, options, start_elo, target_elo, customer_channel_id):
        super().__init__(placeholder="Vyber aktuální Rank zákazníka...", options=options[:25])
        self.start_elo = start_elo
        self.target_elo = target_elo
        self.customer_channel_id = customer_channel_id

    async def callback(self, interaction: discord.Interaction):
        curr_elo = int(self.values[0])
        total_elo = self.target_elo - self.start_elo
        gained_elo = curr_elo - self.start_elo
        
        procento = max(0, min(100, int((gained_elo / total_elo) * 100))) if total_elo > 0 else 100
        rank_name = [r for r, e in RANKS.items() if e == curr_elo][0]
        
        await update_customer_ticket(bot, self.customer_channel_id, procento, f"Aktuální rank: **{rank_name}**")
        await interaction.response.send_message(f"✅ Pokrok aktualizován na **{procento} %** ({rank_name})!", ephemeral=True)

class BoosterPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Check-In", style=discord.ButtonStyle.green, custom_id="booster_checkin")
    async def checkin(self, interaction: discord.Interaction, button: Button):
        ch_id = interaction.channel_id
        checkin_times[ch_id] = time.time()
        if ch_id in active_orders:
            customer_ch = bot.get_channel(active_orders[ch_id]["customer_channel_id"])
            if customer_ch:
                await customer_ch.send("🎮 **Booster se přihlásil na účet a zahájil práci!**")
        await interaction.response.send_message("🟢 **Check-In zaznamenán.**", ephemeral=True)

    @discord.ui.button(label="🔴 Check-Out & Pokrok", style=discord.ButtonStyle.red, custom_id="booster_checkout")
    async def checkout(self, interaction: discord.Interaction, button: Button):
        ch_id = interaction.channel_id
        if ch_id not in active_orders:
            await interaction.response.send_message("❌ Tato zakázka není propojená. Použij admin příkaz `.linkorder`.", ephemeral=True)
            return

        order = active_orders[ch_id]
        if order["type"] == "trophies":
            await interaction.response.send_modal(TrophiesModal(order["start"], order["target"], order["customer_channel_id"]))
        elif order["type"] == "ranked":
            view = RankUpdateView(order["start"], order["target"], order["customer_channel_id"])
            await interaction.response.send_message("Vyber aktuální dosažený Rank:", view=view, ephemeral=True)

async def update_customer_ticket(bot, channel_id, procento, detail_text):
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    plne = round(procento / 10)
    prazdne = 10 - plne
    bar = "▓" * plne + "░" * prazdne
    barva = 0x2ecc71 if procento == 100 else 0x3498db

    embed = discord.Embed(title="🚀 Pokrok v zakázce", color=barva)
    embed.add_field(name="Stav dokončení:", value=f"**{procento} %**", inline=False)
    embed.add_field(name="Ukazatel:", value=f"`{bar}`", inline=False)
    embed.add_field(name="Detail:", value=detail_text, inline=False)
    embed.set_footer(text="Zakázka se aktivně vyvíjí." if procento < 100 else "Zakázka kompletně dokončena! 🎉")

    await channel.send(embed=embed)

@bot.command()
async def linkorder(ctx, typ: str, start: str, target: str, customer_channel_id: int):
    """Propojí booster ticket se zákaznickým ticketem"""
    booster_ch_id = ctx.channel.id
    if typ == "ranked":
        start_val = RANKS.get(start, 0)
        target_val = RANKS.get(target, 1000)
    else:
        start_val, target_val = int(start), int(target)

    active_orders[booster_ch_id] = {
        "type": typ, "start": start_val, "target": target_val, "customer_channel_id": customer_channel_id
    }
    embed = discord.Embed(title="⚙️ Booster Panel aktivní", description=f"Typ: **{typ.upper()}**\nRozsah: **{start} ➡️ {target}**", color=0x2b2d31)
    await ctx.send(embed=embed, view=BoosterPanelView())


# ==========================================
# 2. ČÁST: NÁBOROVÝ SYSTÉM (#CAREER)
# ==========================================

class CareerPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Vyber si pozici, o kterou máš zájem...",
        custom_id="career_select_pos",
        options=[
            discord.SelectOption(label="Booster", value="booster", description="Hraj na účtech a vydělávej", emoji="🎮"),
            discord.SelectOption(label="Moderátor", value="moderator", description="Spravuj chat a tickety", emoji="🛡️"),
            discord.SelectOption(label="Marketing", value="marketing", description="Staraj se o promo a reklamu", emoji="📢"),
        ]
    )
    async def select_pos(self, interaction: discord.Interaction, select: Select):
        position = select.values[0]
        guild = interaction.guild
        user = interaction.user
        channel_name = f"apply-{position}-{user.name.lower()}"

        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message(f"❌ Už máš otevřenou přihlášku v {existing.mention}!", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        ticket_ch = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
        await interaction.response.send_message(f"✅ Přihláška vytvořena: {ticket_ch.mention}", ephemeral=True)

        if position == "booster":
            desc = (
                f"Ahoj {user.mention}, díky za zájem o pozici **Booster**!\n\n"
                "📌 **Pošli sem do chatu tyto podklady:**\n"
                "1️⃣ **Screenshot profilu** z Brawl Stars (musí být vidět **ELO rank** a **pohárky**).\n"
                "2️⃣ Tvůj věk a časové možnosti.\n"
                "3️⃣ Dosavadní zkušenosti."
            )
        elif position == "moderator":
            desc = f"Ahoj {user.mention}, napiš nám svůj věk, zkušenosti s moderováním a kolik času můžeš trávit na serveru."
        else:
            desc = f"Ahoj {user.mention}, popiš nám své zkušenosti s marketingem, sítěmi a jaké máš nápady na propagaci."

        embed = discord.Embed(title=f"📋 Žádost o pozici: {position.capitalize()}", description=desc, color=0xf1c40f)
        await ticket_ch.send(content=f"{user.mention}", embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_career(ctx):
    """Vytvoří náborový panel v kanálu #career"""
    try: await ctx.message.delete()
    except: pass
    
    embed = discord.Embed(
        title="💼 Staň se součástí našeho týmu!",
        description="Chceš si vydělat boostováním, moderovat komunitu nebo dělat marketing?\n\n👇 **Vyber pozici v menu níže a otevři si přihlášku:**",
        color=0x2ecc71
    )
    await ctx.send(embed=embed, view=CareerPanelView())


# ==========================================
# 3. ČÁST: NÁSTROJE, ŠABLONY A PŘÍKAZY
# ==========================================

@bot.command()
async def review(ctx):
    """Pošle šablonu pro recenzi do ticketu"""
    try: await ctx.message.delete()
    except: pass

    embed = discord.Embed(
        title="⭐ Děkujeme za využití našich služeb!",
        description="Budeme moc rádi za krátkou recenzi/vouch v příslušném kanálu!\n\n👇 **Můžeš zkopírovat tuto šablonu:**",
        color=0xf1c40f
    )
    sablona = "```text\n+rep @FrostSTORE\nSlužba: Ranked Boost / Pohárky\nRychlost: 10/10\nKomunikace: 10/10\nHodnocení: Super domluva, doporučuji!\n```"
    embed.add_field(name="📝 Šablona k zkopírování:", value=sablona, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_tools(ctx):
    """Vloží dokumentaci příkazů do kanálu"""
    try: await ctx.message.delete()
    except: pass

    e1 = discord.Embed(
        title="🎮 Nástroje pro Boostery",
        description="• **Check-In / Check-Out:** Tlačítka v booster ticketu pro měření času a zápis progressu (% / ELO / Pohárky).\n• `.review` — Pošle zákazníkovi šablonu pro napsání vouchu/recenze.",
        color=0x3498db
    )
    e2 = discord.Embed(
        title="⚙️ Admin & Setup Příkazy",
        description="• `.linkorder [ranked/trophies] [start] [target] [ID_zakaznickeho_ticketu]` — Propojení ticketů.\n• `.setup_career` — Vytvoří náborový panel v #career.\n• `.setup_tools` — Zobrazí tento manuál.",
        color=0xe74c3c
    )
    await ctx.send(embed=e1)
    await ctx.send(embed=e2)

# Spuštění bota (nahraď svým tokenem)
token = os.getenv("BOT_TOKEN", "TVUJ_BOT_TOKEN")
bot.run(token)

