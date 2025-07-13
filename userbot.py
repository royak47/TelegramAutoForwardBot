import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import ResolveUsernameRequest

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

SETTINGS_FILE = "settings.json"
FORWARD_STATUS_FILE = "forward_status.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Load JSON utility
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

# Check if forwarding is enabled
def is_forwarding_enabled():
    return load_json(FORWARD_STATUS_FILE).get("forwarding", True)

# Normalize input (username, link, id)
def normalize_channel_identifier(raw):
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        return raw.replace("https://t.me/", "@")
    elif raw.startswith("t.me/"):
        return raw.replace("t.me/", "@")
    return raw

@client.on(events.NewMessage())
async def handle_message(event):
    if not is_forwarding_enabled():
        print("🚫 Forwarding is OFF")
        return

    settings = load_json(SETTINGS_FILE)
    source_channels_raw = settings.get("source_channels", [])
    target_channels_raw = settings.get("target_channels", [])

    # Normalize all source channels
    source_channels = [normalize_channel_identifier(ch) for ch in source_channels_raw]
    target_channels = [normalize_channel_identifier(ch) for ch in target_channels_raw]

    # Identify sender
    sender = await event.get_chat()
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None

    print(f"📨 Incoming from ID: {chat_id}, Username: {username}")

    matched = False
    for src in source_channels:
        if src.startswith("-100") and src == chat_id:
            matched = True
        elif username and src.lower() == username:
            matched = True
        elif src.startswith("@") and username and src.lower() == username.lower():
            matched = True

    if not matched:
        print("⚠️ Not a listed source channel, skipping.")
        return

    # Send to all targets
    for target in target_channels:
        try:
            print(f"⏩ Sending to {target}")
            await client.send_message(target, message=event.message.message or "", file=event.message.media)
            print(f"✅ Sent to {target}")
        except Exception as e:
            print(f"❌ Failed to send to {target}: {e}")

print("🚀 Userbot is running...")
client.start()
client.run_until_disconnected()
