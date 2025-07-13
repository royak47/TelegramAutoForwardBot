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
    with open(file, "r") as f:
        return json.load(f)

def normalize_source(source):
    source = str(source).strip().lower()
    if source.startswith("https://t.me/"):
        source = "@" + source.split("/")[-1]
    elif source.startswith("t.me/"):
        source = "@" + source.split("/")[-1]
    return source

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)

    if not event.chat:
        return

    chat_id = str(event.chat.id).strip()
    chat_username = f"@{event.chat.username}".lower() if event.chat.username else None

    source_channels = [normalize_source(c) for c in settings["source_channels"]]

    # Check if source matches by ID or @username
    if chat_id not in source_channels and chat_username not in source_channels:
        print(f"⚠️ Ignored message from: {chat_id} {chat_username}")
        return

    msg = event.message
    text = msg.message or ""

    # Apply replacements
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    for target in settings["target_channels"]:
        try:
            await client.send_message(target, file=msg.media, message=text)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

print("📦 Userbot started.")
client.start()
client.run_until_disconnected()
