import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def normalize(source):
    if source.startswith("https://t.me/"):
        return "@" + source.split("/")[-1]
    elif source.startswith("t.me/"):
        return "@" + source.split("/")[-1]
    return source.strip()

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)

    sender = await event.get_chat()
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None

    # Normalize all sources
    normalized_sources = [normalize(src).lower() for src in settings.get("source_channels", [])]

    if chat_id not in normalized_sources and (username and username not in normalized_sources):
        print(f"⚠️ Message ignored from: {chat_id} {username}")
        return

    msg = event.message
    text = msg.message or ""

    # Replace text and links
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    for target in settings.get("target_channels", []):
        try:
            await client.send_message(target, message=text, file=msg.media)
            print(f"✅ Sent to {target}")
        except Exception as e:
            print(f"❌ Failed to send to {target}: {e}")

print("📦 Userbot started.")
client.start()
client.run_until_disconnected()
