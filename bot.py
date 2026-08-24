import os
import re
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = Thread(target=run_web)
    thread.start()


# =========================================================
# CONFIG
# =========================================================

ROLE_SLUJBA_ID = 1541403780866646106


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# VIEW - BUTON INCHEIERE SLUJBA
# =========================================================

class SlujbaView(discord.ui.View):
    def __init__(self):
        # timeout=None => persistent
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Încheiere slujbă",
        emoji="✅",
        style=discord.ButtonStyle.danger,
        custom_id="slujba_incheiere"
    )
    async def incheiere_slujba(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        # Verificăm embed-ul mesajului
        if not interaction.message.embeds:
            await interaction.response.send_message(
                "❌ Nu am putut identifica slujba.",
                ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]

        # ID-ul persoanei care a creat slujba este salvat în footer
        footer_text = embed.footer.text or ""

        match = re.search(r"Autor ID: (\d+)", footer_text)

        if not match:
            await interaction.response.send_message(
                "❌ Nu am putut identifica persoana care a creat slujba.",
                ephemeral=True
            )
            return

        autor_id = int(match.group(1))

        # Doar cel care a creat slujba poate apăsa
        if interaction.user.id != autor_id:
            await interaction.response.send_message(
                "❌ Doar persoana care a început această slujbă o poate încheia.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📸 **Trimite acum o poză în acest canal.**\n\n"
            "Poți:\n"
            "• să dai copy-paste la imagine\n"
            "• să o tragi în Discord\n"
            "• să o trimiți ca fișier\n\n"
            "Ai **2 minute** la dispoziție.",
            ephemeral=True
        )

        # Verificăm ca mesajul să fie:
        # - de la aceeași persoană
        # - în același canal
        # - să conțină attachment
        def check(message: discord.Message):
            return (
                message.author.id == interaction.user.id
                and message.channel.id == interaction.channel.id
                and len(message.attachments) > 0
            )

        try:
            mesaj_poza = await interaction.client.wait_for(
                "message",
                timeout=120,
                check=check
            )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "⏰ Timpul a expirat. Apasă din nou pe **Încheiere slujbă**.",
                ephemeral=True
            )
            return

        # Căutăm prima imagine
        poza = None

        for attachment in mesaj_poza.attachments:

            if attachment.content_type:
                if attachment.content_type.startswith("image/"):
                    poza = attachment
                    break

            # fallback dacă Discord nu trimite content_type
            nume = attachment.filename.lower()

            if nume.endswith(
                (".png", ".jpg", ".jpeg", ".webp", ".gif")
            ):
                poza = attachment
                break

        if poza is None:
            await interaction.followup.send(
                "❌ Fișierul trimis nu pare să fie o imagine.\n"
                "Apasă din nou pe **Încheiere slujbă** și trimite o poză.",
                ephemeral=True
            )
            return

        # =====================================================
        # MODIFICĂM EMBED-UL
        # =====================================================

        embed.color = discord.Color.green()

        # Schimbăm statusul
        status_gasit = False

        for index, field in enumerate(embed.fields):

            if field.name == "Status":
                embed.set_field_at(
                    index,
                    name="Status",
                    value="✅ Slujbă încheiată",
                    inline=False
                )

                status_gasit = True
                break

        if not status_gasit:
            embed.add_field(
                name="Status",
                value="✅ Slujbă încheiată",
                inline=False
            )

        # Adăugăm poza
        embed.set_image(url=poza.url)

        # Timpul încheierii
        embed.add_field(
            name="🕐 Încheiată",
            value=f"<t:{int(discord.utils.utcnow().timestamp())}:F>",
            inline=False
        )

        # Dezactivăm butonul
        button.disabled = True
        button.label = "Slujbă încheiată"
        button.style = discord.ButtonStyle.secondary

        await interaction.message.edit(
            embed=embed,
            view=self
        )

        await interaction.followup.send(
            "✅ Slujba a fost încheiată și poza a fost adăugată.",
            ephemeral=True
        )


# =========================================================
# MODAL /SLUJBA
# =========================================================

class SlujbaModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Creare slujbă"
        )

    locatie = discord.ui.TextInput(
        label="Locație",
        placeholder="Ex: Los Santos",
        required=True,
        max_length=100
    )

    protos = discord.ui.TextInput(
        label="Protos",
        placeholder="Ex: Numele / informația dorită",
        required=True,
        max_length=100
    )

    tip_slujba = discord.ui.TextInput(
        label="Tip Slujbă",
        placeholder="Ex: Slujbă normală",
        required=True,
        max_length=100
    )

    ora_inceperii = discord.ui.TextInput(
        label="Ora începerii",
        placeholder="Ex: 20:30",
        required=True,
        max_length=50
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        # =====================================================
        # EMBED
        # =====================================================

        embed = discord.Embed(
            title="⛪ Slujbă nouă",
            description=(
                "A fost anunțată o nouă slujbă.\n"
                "Detaliile sunt disponibile mai jos."
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📍 Locație",
            value=self.locatie.value,
            inline=False
        )

        embed.add_field(
            name="📋 Protos",
            value=self.protos.value,
            inline=False
        )

        embed.add_field(
            name="⛪ Tip Slujbă",
            value=self.tip_slujba.value,
            inline=False
        )

        embed.add_field(
            name="🕐 Ora începerii",
            value=self.ora_inceperii.value,
            inline=False
        )

        embed.add_field(
            name="Status",
            value="🟢 În desfășurare",
            inline=False
        )

        embed.set_author(
            name=f"Creată de {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        # Aici salvăm ID-ul creatorului
        # Este folosit de buton pentru verificare
        embed.set_footer(
            text=f"Autor ID: {interaction.user.id}"
        )

        view = SlujbaView()

        # Răspuns ephemeral la comandă
        await interaction.response.send_message(
            "✅ Slujba a fost creată.",
            ephemeral=True
        )

        # Mesaj public
        await interaction.channel.send(
            content="@here",
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(
                everyone=True
            )
        )


# =========================================================
# /SLUJBA
# =========================================================

@bot.tree.command(
    name="slujba",
    description="Creează un anunț pentru o slujbă."
)
async def slujba(interaction: discord.Interaction):

    # Comanda trebuie folosită pe server
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ Această comandă poate fi folosită doar pe server.",
            ephemeral=True
        )
        return

    # Căutăm rolul necesar
    rol = interaction.guild.get_role(ROLE_SLUJBA_ID)

    if rol is None:
        await interaction.response.send_message(
            "❌ Rolul configurat pentru această comandă nu există.",
            ephemeral=True
        )
        return

    # Verificăm dacă utilizatorul are rolul
    if rol not in interaction.user.roles:
        await interaction.response.send_message(
            "❌ Nu ai permisiunea să folosești comanda `/slujba`.",
            ephemeral=True
        )
        return

    # Deschidem formularul
    await interaction.response.send_modal(
        SlujbaModal()
    )


# =========================================================
# /PING
# =========================================================

@bot.tree.command(
    name="ping",
    description="Verifică dacă botul funcționează."
)
async def ping(interaction: discord.Interaction):

    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🏓 Pong! `{latency}ms`"
    )


# =========================================================
# /HELLO
# =========================================================

@bot.tree.command(
    name="hello",
    description="Botul îți spune salut."
)
async def hello(interaction: discord.Interaction):

    await interaction.response.send_message(
        f"Salut, {interaction.user.mention}! 👋"
    )


# =========================================================
# !TEST
# =========================================================

@bot.command()
async def test(ctx):

    await ctx.send(
        "Botul funcționează! ✅"
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(f"Bot conectat ca {bot.user}")
    print(f"ID: {bot.user.id}")

    # Înregistrăm view-ul persistent.
    # Astfel butonul poate continua să funcționeze și după restart.
    bot.add_view(SlujbaView())

    try:

        synced = await bot.tree.sync()

        print(
            f"Au fost sincronizate "
            f"{len(synced)} comenzi slash."
        )

    except Exception as e:

        print(
            f"Eroare la sincronizarea comenzilor: {e}"
        )


# =========================================================
# TOKEN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN nu a fost setat."
    )


bot.run(TOKEN)keep_alive()
bot.run(TOKEN)
