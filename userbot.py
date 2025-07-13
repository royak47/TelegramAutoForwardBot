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
BLACKLIST_FILE = "blacklist.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    blacklist = load_json(BLACKLIST_FILE).get("words", [])

    source_channels = [s.lower() for s in settings.get("source_channels", [])]
    target_channels = settings.get("target_channels", [])

    # Get source ID and username
    sender = await event.get_chat()
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else ""

    # Validate: Must be in allowed source_channels
    if chat_id not in source_channels and username not in source_channels:
        return  # silently ignore without logging

    msg = event.message
    text = msg.message or ""

    # Blacklist check
    if any(word.lower() in text.lower() for word in blacklist):
        return

    # Replace words and links
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    # Forward to targets
    for target in target_channels:
        try:
            await client.send_message(target, file=msg.media, message=text)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
