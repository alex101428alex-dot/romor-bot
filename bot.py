import os
import re
import io
import asyncio
import discord

from discord.ext import commands
from discord import app_commands

from flask import Flask
from threading import Thread


# =========================================================
# CONFIG
# =========================================================

ROLE_SLUJBA_ID = 1541403780866646106
GUILD_ID = 1526909089664471141


# =========================================================
# SERVER WEB PENTRU RENDER
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot online!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    Thread(target=run_web, daemon=True).start()


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
        if not interaction.message.embeds:
            await interaction.response.send_message(
                "❌ Nu am putut identifica slujba.",
                ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]
        footer_text = embed.footer.text or ""

        match = re.search(r"Autor ID: (\d+)", footer_text)

        if not match:
            await interaction.response.send_message(
                "❌ Nu am putut identifica persoana care a creat slujba.",
                ephemeral=True
            )
            return

        autor_id = int(match.group(1))

        if interaction.user.id != autor_id:
            await interaction.response.send_message(
                "❌ Doar persoana care a început această slujbă o poate încheia.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📸 Trimite acum o poză în acest canal.\n\n"
            "Poți da copy-paste la imagine, o poți trage în Discord "
            "sau o poți trimite ca fișier.\n\n"
            "Ai **2 minute** la dispoziție.",
            ephemeral=True
        )

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

        poza = None

        for attachment in mesaj_poza.attachments:
            if (
                attachment.content_type
                and attachment.content_type.startswith("image/")
            ):
                poza = attachment
                break

            nume = attachment.filename.lower()
            if nume.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                poza = attachment
                break

        if poza is None:
            await interaction.followup.send(
                "❌ Fișierul trimis nu pare să fie o imagine.\n"
                "Apasă din nou pe **Încheiere slujbă** și trimite o poză.",
                ephemeral=True
            )
            return

        # Descărcăm poza înainte să ștergem mesajul utilizatorului.
        try:
            poza_bytes = await poza.read()
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ Nu am reușit să descarc poza. Încearcă din nou.",
                ephemeral=True
            )
            return

        fisier = discord.File(
            io.BytesIO(poza_bytes),
            filename=poza.filename
        )

        embed.color = discord.Color.green()

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

        embed.add_field(
            name="🕐 Încheiată",
            value=f"<t:{int(discord.utils.utcnow().timestamp())}:F>",
            inline=False
        )

        embed.set_image(
            url=f"attachment://{poza.filename}"
        )

        button.disabled = True
        button.label = "Slujbă încheiată"
        button.style = discord.ButtonStyle.secondary

        try:
            await interaction.message.edit(
                embed=embed,
                view=self,
                attachments=[fisier]
            )
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ Nu am reușit să actualizez mesajul slujbei.",
                ephemeral=True
            )
            return

        # Ștergem mesajul original care conținea poza.
        try:
            await mesaj_poza.delete()
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ Slujba a fost încheiată, dar nu pot șterge mesajul "
                "cu poza. Botul are nevoie de permisiunea **Manage Messages**.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            "✅ Slujba a fost încheiată, poza a fost salvată în mesajul botului, "
            "iar mesajul tău cu poza a fost șters.",
            ephemeral=True
        )


# =========================================================
# MODAL - CREARE SLUJBA
# =========================================================

class SlujbaModal(discord.ui.Modal):
    def __init__(self, protos: discord.Member):
        super().__init__(title="Creare slujbă")
        self.protos = protos

    locatie = discord.ui.TextInput(
        label="Locație",
        placeholder="Ex: Catedrala",
        required=True,
        max_length=100
    )

    tip_slujba = discord.ui.TextInput(
        label="Tip Slujbă",
        placeholder="Ex: Vecernie",
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
        embed = discord.Embed(
            title="⛪ Slujbă nouă",
            description="A fost anunțată o nouă slujbă.",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📍 Locație",
            value=self.locatie.value,
            inline=False
        )

        embed.add_field(
            name="👤 Protos",
            value=self.protos.mention,
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

        # Salvăm ID-ul creatorului pentru verificarea butonului.
        embed.set_footer(
            text=f"Autor ID: {interaction.user.id}"
        )

        view = SlujbaView()

        await interaction.response.send_message(
            "✅ Slujba a fost creată.",
            ephemeral=True
        )

        await interaction.channel.send(
            content="@here",
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(
                everyone=True,
                users=True,
                roles=False
            )
        )


# =========================================================
# /SLUJBA
# =========================================================

@bot.tree.command(
    name="slujba",
    description="Creează un anunț pentru o slujbă."
)
@app_commands.describe(
    protos="Alege persoana care va fi Protos"
)
async def slujba(
    interaction: discord.Interaction,
    protos: discord.Member
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ Această comandă poate fi folosită doar pe server.",
            ephemeral=True
        )
        return

    rol = interaction.guild.get_role(ROLE_SLUJBA_ID)

    if rol is None:
        await interaction.response.send_message(
            "❌ Rolul configurat pentru această comandă nu există.",
            ephemeral=True
        )
        return

    if rol not in interaction.user.roles:
        await interaction.response.send_message(
            "❌ Nu ai permisiunea să folosești comanda `/slujba`.",
            ephemeral=True
        )
        return

    await interaction.response.send_modal(
        SlujbaModal(protos)
    )


# =========================================================
# /MESAJ_ROL
# =========================================================

ROLE_MESAJ_PERMISSION_ID = 1541422525001506887


@bot.tree.command(
    name="mesaj_rol",
    description="Trimite un mesaj privat tuturor persoanelor cu un anumit rol."
)
@app_commands.describe(
    rol="Rolul persoanelor cărora vrei să le trimiți mesajul",
    mesaj="Mesajul care va fi trimis în privat"
)
async def mesaj_rol(
    interaction: discord.Interaction,
    rol: discord.Role,
    mesaj: str
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ Această comandă poate fi folosită doar pe server.",
            ephemeral=True
        )
        return

    rol_permisiune = interaction.guild.get_role(ROLE_MESAJ_PERMISSION_ID)

    if rol_permisiune is None:
        await interaction.response.send_message(
            "❌ Rolul de permisiune configurat nu există.",
            ephemeral=True
        )
        return

    if rol_permisiune not in interaction.user.roles:
        await interaction.response.send_message(
            "❌ Nu ai permisiunea să folosești această comandă.",
            ephemeral=True
        )
        return

    membri = [membru for membru in rol.members if not membru.bot]

    if not membri:
        await interaction.response.send_message(
            f"⚠️ Nu am găsit niciun membru cu rolul {rol.mention}.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"📨 Încep să trimit mesajul membrilor cu rolul {rol.mention}...",
        ephemeral=True
    )

    trimise = 0
    esuate = 0

    for membru in membri:
        try:
            embed = discord.Embed(
                title="📩 Mesaj nou",
                description=mesaj,
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Server",
                value=interaction.guild.name,
                inline=False
            )

            embed.set_footer(
                text=f"Trimis de {interaction.user.display_name}"
            )

            await membru.send(embed=embed)
            trimise += 1
            await asyncio.sleep(0.5)

        except discord.Forbidden:
            esuate += 1

        except discord.HTTPException:
            esuate += 1

    await interaction.followup.send(
        f"✅ **Trimitere terminată!**\n\n"
        f"👥 Rol: {rol.mention}\n"
        f"📨 Mesaje trimise: **{trimise}**\n"
        f"❌ Mesaje eșuate: **{esuate}**",
        ephemeral=True
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
    await ctx.send("Botul funcționează! ✅")


# =========================================================
# SETUP / SINCRONIZARE
# =========================================================

@bot.event
async def on_ready():
    print(f"Bot conectat ca {bot.user}")
    print(f"ID: {bot.user.id}")


async def setup_bot():
    # View persistent: butonul continuă să funcționeze și după restart.
    bot.add_view(SlujbaView())

    guild = discord.Object(id=GUILD_ID)

    try:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)

        print(
            f"Au fost sincronizate {len(synced)} comenzi "
            f"pe serverul {GUILD_ID}."
        )
    except Exception as e:
        print(f"Eroare la sincronizarea comenzilor: {e}")


# =========================================================
# TOKEN / START
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN nu a fost setat.")


async def main():
    async with bot:
        await setup_bot()
        await bot.start(TOKEN)


keep_alive()
asyncio.run(main())
