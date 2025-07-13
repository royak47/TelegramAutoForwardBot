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
FORWARD_STATUS_FILE = "forward_status.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def is_forwarding_enabled():
    data = load_json(FORWARD_STATUS_FILE)
    return data.get("forwarding", True)

@client.on(events.NewMessage())
async def handle_new_message(event):
    if not is_forwarding_enabled():
        return

    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)

    source_channels = settings.get("source_channels", [])
    target_channels = settings.get("target_channels", [])

    # Get unique ID or username
    sender = await event.get_chat()
    chat_id = sender.id
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None

    if str(chat_id) not in source_channels and username not in [c.lower() for c in source_channels]:
        return  # not a valid source

    msg = event.message
    text = msg.message or ""

    # Replace words and links
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    # Forward to all targets
    for target in target_channels:
        try:
            await client.send_message(target, message=text, file=msg.media)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

# Start bot
print("🤖 Userbot started and listening...")
client.start()
client.run_until_disconnected()
