import discord
from discord.ext import commands
import easyocr
import re
import os
import json
from PIL import Image
import requests

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

reader = easyocr.Reader(['en'])

DATA_FILE = "donations.json"

# Load data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        donations = json.load(f)
else:
    donations = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(donations, f, indent=4)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def weekly(ctx):
    if not donations:
        await ctx.send("No donation data yet.")
        return

    sorted_data = sorted(
        donations.items(),
        key=lambda x: x[1],
        reverse=True
    )

    msg = "🏆 Weekly Donations\n\n"

    for name, amount in sorted_data:
        warning = " ⚠️" if amount < 10000 else ""
        msg += f"{name} — {amount}{warning}\n"

    await ctx.send(msg)

@bot.command()
async def defaulters(ctx):
    msg = "⚠️ Members below 10k\n\n"

    found = False

    for name, amount in donations.items():
        if amount < 10000:
            msg += f"{name} — {amount}\n"
            found = True

    if not found:
        msg += "Nobody is below 10k."

    await ctx.send(msg)

@bot.command()
async def resetweek(ctx):
    donations.clear()
    save_data()
    await ctx.send("Weekly donations reset.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    if not message.attachments:
        return

    for attachment in message.attachments:

        if attachment.filename.endswith((".png", ".jpg", ".jpeg")):

            file_path = "temp_image.png"

            response = requests.get(attachment.url)

            with open(file_path, "wb") as f:
                f.write(response.content)

            results = reader.readtext(file_path, detail=0)

            joined = " ".join(results)

            pattern = r'([A-Za-z0-9_]+)\s+(\d+\.\d+K|\d+)'

            matches = re.findall(pattern, joined)

            updated = []

            for name, amount in matches:

                amount = amount.replace("K", "")

                try:
                    value = float(amount) * 1000
                except:
                    continue

                donations[name] = int(value)
                updated.append(f"{name} — {int(value)}")

            save_data()

            if updated:
                msg = "✅ Updated Donations\n\n"
                msg += "\n".join(updated)
                await message.channel.send(msg)
            else:
                await message.channel.send(
                    "Couldn't read donation data clearly."
                )

bot.run(TOKEN)
