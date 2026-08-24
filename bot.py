import os
import asyncio
import discord

from discord.ext import commands
from discord import app_commands

from flask import Flask
from threading import Thread


# =========================================================
# CONFIG
# =========================================================

GUILD_ID = 1526909089664471141
ROLE_MESAJ_PERMISSION_ID = 1541422525001506887


# =========================================================
# SERVER WEB PENTRU RENDER
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot online!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


def keep_alive():
    Thread(
        target=run_web,
        daemon=True
    ).start()


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

comenzi_sincronizate = False


# =========================================================
# /MESAJ_ROL
# =========================================================

@bot.tree.command(
    name="mesaj_rol",
    description="Trimite un mesaj privat tuturor membrilor care au un anumit rol."
)
@app_commands.describe(
    rol_id="ID-ul rolului care trebuie să primească mesajul",
    mesaj="Mesajul care va fi trimis în privat"
)
async def mesaj_rol(
    interaction: discord.Interaction,
    rol_id: str,
    mesaj: str
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ Această comandă poate fi folosită doar pe server.",
            ephemeral=True
        )
        return

    rol_permisiune = interaction.guild.get_role(
        ROLE_MESAJ_PERMISSION_ID
    )

    if rol_permisiune is None:
        await interaction.response.send_message(
            "❌ Rolul de permisiune configurat nu există pe server.",
            ephemeral=True
        )
        return

    if rol_permisiune not in interaction.user.roles:
        await interaction.response.send_message(
            "❌ Nu ai permisiunea să folosești `/mesaj_rol`.",
            ephemeral=True
        )
        return

    try:
        target_role_id = int(rol_id.strip())
    except ValueError:
        await interaction.response.send_message(
            "❌ ID-ul rolului nu este valid. Introdu doar cifre.",
            ephemeral=True
        )
        return

    rol_tinta = interaction.guild.get_role(target_role_id)

    if rol_tinta is None:
        await interaction.response.send_message(
            "❌ Nu am găsit niciun rol cu acel ID pe acest server.",
            ephemeral=True
        )
        return

    if len(mesaj) > 4000:
        await interaction.response.send_message(
            "❌ Mesajul este prea lung. Folosește maximum 4000 de caractere.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True,
        thinking=True
    )

    try:
        if not interaction.guild.chunked:
            await interaction.guild.chunk(cache=True)
    except Exception as e:
        print(f"Nu am putut încărca lista completă de membri: {e}")

    membri = [
        membru
        for membru in interaction.guild.members
        if rol_tinta in membru.roles and not membru.bot
    ]

    if not membri:
        await interaction.followup.send(
            f"⚠️ Nu am găsit niciun membru cu rolul **{rol_tinta.name}**.",
            ephemeral=True
        )
        return

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

        except discord.HTTPException as e:
            esuate += 1
            print(
                f"Eroare DM către {membru} ({membru.id}): {e}"
            )

    await interaction.followup.send(
        "✅ **Trimitere terminată!**\n\n"
        f"🎯 Rol: **{rol_tinta.name}** (`{rol_tinta.id}`)\n"
        f"👥 Membri găsiți: **{len(membri)}**\n"
        f"📨 Mesaje trimise: **{trimise}**\n"
        f"❌ Mesaje eșuate: **{esuate}**",
        ephemeral=True
    )


# =========================================================
# READY / SINCRONIZARE
# =========================================================

@bot.event
async def on_ready():
    global comenzi_sincronizate

    print(f"Bot conectat ca {bot.user}")
    print(f"ID: {bot.user.id}")

    if comenzi_sincronizate:
        return

    guild = discord.Object(id=GUILD_ID)

    try:
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)

        synced = await bot.tree.sync(guild=guild)

        print(
            f"Au fost sincronizate {len(synced)} comenzi "
            f"pe serverul {GUILD_ID}."
        )

        comenzi_sincronizate = True

    except Exception as e:
        print(f"Eroare la sincronizarea comenzilor: {e}")


# =========================================================
# TOKEN / START
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN nu a fost setat."
    )


keep_alive()
bot.run(TOKEN)
