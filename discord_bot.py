import discord
import requests
import os
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

CHATBOT_WEBHOOK_URL = "https://yarnhub-backend.onrender.com/webhook"

if not DISCORD_TOKEN:
    print("❌ Error: DISCORD_BOT_TOKEN not found in .env")
    exit()

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # <-- MUST be enabled in Dev Portal too
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user} (ID: {client.user.id})")
    print("------ Bot is running ------")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    print(f"📩 Received message in #{message.channel}: {message.content}")

    # Simple rule: reply to every message
    question = message.content.strip()
    processing_message = await message.channel.send("🤖 Thinking...")

    try:
        response = requests.post(CHATBOT_WEBHOOK_URL, json={"message": question}, timeout=60)
        if response.status_code == 200:
            ai_reply = response.json().get("reply", "Sorry, no reply.")
            await processing_message.edit(content=ai_reply)
        else:
            await processing_message.edit(content="⚠️ Brain is slow, try again later.")
    except Exception as e:
        print(f"❌ Error: {e}")
        await processing_message.edit(content="❌ Could not reach brain.")

# --- RUN BOT ---
print("🚀 Starting bot...")
client.run(DISCORD_TOKEN)
