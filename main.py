import discord
from discord.ext import commands
import re
import os
import json
import requests

# ======================
# SETTINGS
# ======================

TOKEN = os.getenv("DISCORD_TOKEN")

HF_URL = "https://akiro1982-zenith-token-bot.hf.space/run/predict"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "donations.json"

# ======================
# LOAD DATA
# ======================

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        donations = json.load(f)
else:
    donations = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(donations, f, indent=4)

# ======================
# HUGGING FACE FUNCTION
# ======================

def analyze_image(image_bytes):
    response = requests.post(
        HF_URL,
        json={"data": [image_bytes]}
    )
    return response.json()

# ======================
# BOT READY
# ======================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ======================
# COMMANDS (UNCHANGED LOGIC)
# ======================

@bot.command()
async def weekly(ctx):
    if not donations:
        await ctx.send("No donation data yet.")
        return

    sorted_data = sorted(donations.items(), key=lambda x: x[1], reverse=True)

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

# ======================
# IMAGE HANDLER (HF VERSION)
# ======================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # process commands first
    await bot.process_commands(message)

    if not message.attachments:
        return

    for attachment in message.attachments:

        if attachment.filename.endswith((".png", ".jpg", ".jpeg")):

            image_bytes = await attachment.read()

            result = analyze_image(image_bytes)

            # HF returns: ["text"]
            try:
                text = result["data"][0]
            except:
                await message.channel.send("Error reading image from HF.")
                return

            # ======================
            # PARSE DONATIONS
            # ======================

            pattern = r'([A-Za-z0-9_]+)\s+(\d+\.?\d*K?|\d+)'
            matches = re.findall(pattern, text)

            updated = []

            for name, amount in matches:

                amount = amount.replace("K", "")

                try:
                    value = float(amount) * 1000 if "K" in amount else float(amount)
                except:
                    continue

                donations[name] = int(value)
                updated.append(f"{name} — {int(value)}")

            save_data()

            if updated:
                msg = "✅ Updated Donations\n\n" + "\n".join(updated)
                await message.channel.send(msg)
            else:
                await message.channel.send("Couldn't read donation data clearly.")

# ======================
# RUN BOT
# ======================

bot.run(TOKEN)
