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


# Utility Functions
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def is_forwarding_enabled():
    data = load_json(FORWARD_STATUS_FILE)
    return data.get("forwarding", True)

def match_source(chat_id, username, sources):
    username = username.lower() if username else ""
    return (
        str(chat_id) in sources
        or f"@{username}" in [c.lower() for c in sources]
        or f"https://t.me/{username}" in [c.lower() for c in sources]
    )

# Unified forwarding function (new + edited)
async def forward_message(event):
    if not is_forwarding_enabled():
        print("⏸ Forwarding is disabled. Skipping.")
        return

    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)

    source_channels = settings.get("source_channels", [])
    target_channels = settings.get("target_channels", [])

    sender = await event.get_chat()
    chat_id = sender.id
    username = getattr(sender, 'username', None)

    if not match_source(chat_id, username, source_channels):
        print(f"⛔ Message skipped (not in source): {username or chat_id}")
        return

    msg = event.message
    text = msg.message or ""

    # Word & link replacement
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    # Forwarding logic
    for target in target_channels:
        try:
            await client.send_message(target, message=text, file=msg.media)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

# Message events
@client.on(events.NewMessage())
async def new_message_handler(event):
    await forward_message(event)

@client.on(events.MessageEdited())
async def edited_message_handler(event):
    await forward_message(event)

# Start the client
print("🤖 Userbot started and listening...")
client.start()
client.run_until_disconnected()
