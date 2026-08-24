import os
import discord
from discord.ext import commands

# Intents
intents = discord.Intents.default()
intents.message_content = True

# Bot
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Bot conectat ca {bot.user}")
    print(f"ID: {bot.user.id}")

    try:
        synced = await bot.tree.sync()
        print(f"Au fost sincronizate {len(synced)} comenzi slash.")
    except Exception as e:
        print(f"Eroare la sincronizarea comenzilor: {e}")


@bot.tree.command(name="ping", description="Verifică dacă botul funcționează.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🏓 Pong! `{latency}ms`"
    )


@bot.tree.command(name="hello", description="Botul îți spune salut.")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Salut, {interaction.user.mention}! 👋"
    )


@bot.command()
async def test(ctx):
    await ctx.send("Botul funcționează! ✅")


# Tokenul este luat din variabila de mediu.
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN nu a fost setat.")

bot.run(TOKEN)