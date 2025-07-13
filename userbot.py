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

# Normalize username/link/ID
def normalize(raw):
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        return "@" + raw.split("https://t.me/")[-1]
    elif raw.startswith("t.me/"):
        return "@" + raw.split("t.me/")[-1]
    return raw

@client.on(events.NewMessage(chats=None))  # all chats
async def handle_message(event):
    if not is_forwarding_enabled():
        return

    settings = load_json(SETTINGS_FILE)
    source_channels_raw = settings.get("source_channels", [])
    target_channels_raw = settings.get("target_channels", [])

    # Normalize all sources and targets
    source_channels = [normalize(ch).lower() for ch in source_channels_raw]
    target_channels = [normalize(ch) for ch in target_channels_raw]

    sender = await event.get_chat()
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None

    if not sender.broadcast:
        print("❌ Not a channel, skipping.")
        return

    print(f"📨 From channel: ID = {chat_id}, Username = {username}")

    # Check if this is an allowed source
    matched = False
    for src in source_channels:
        if src == chat_id or (username and src == username):
            matched = True
            break

    if not matched:
        print("⚠️ Not in allowed source_channels.")
        return

    # Forward to all target channels
    for target in target_channels:
        try:
            print(f"⏩ Sending to {target}")
            await client.send_message(entity=target, message=event.message.message or "", file=event.message.media)
            print(f"✅ Sent to {target}")
        except Exception as e:
            print(f"❌ Failed to send to {target}: {e}")

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
