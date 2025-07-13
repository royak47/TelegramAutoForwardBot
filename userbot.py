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
FILTER_FILE = "filters.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def is_forwarding_enabled():
    return load_json(FORWARD_STATUS_FILE).get("forwarding", True)

def match_source(chat_id, username, sources):
    username = username.lower() if username else ""
    return (
        str(chat_id) in sources or
        f"@{username}" in [c.lower() for c in sources] or
        f"https://t.me/{username}" in [c.lower() for c in sources]
    )

def filter_match(event, filters):
    msg = event.message

    if filters.get("only_text") and not msg.message:
        return False
    if filters.get("only_image") and not (msg.photo or getattr(msg.media, 'document', None)):
        return False
    if filters.get("only_video") and not (msg.video or msg.document and 'video' in str(msg.document.mime_type)):
        return False
    if filters.get("only_link"):
        if not msg.message or "http" not in msg.message:
            return False

    return True

@client.on(events.NewMessage())
async def handle_message(event):
    if not is_forwarding_enabled():
        return

    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    filters = load_json(FILTER_FILE)

    source_channels = settings.get("source_channels", [])
    target_channels = settings.get("target_channels", [])

    sender = await event.get_chat()
    chat_id = sender.id
    username = getattr(sender, 'username', None)

    if not match_source(chat_id, username, source_channels):
        return

    if not filter_match(event, filters):
        print("⏩ Message skipped by filter.")
        return

    msg = event.message
    text = msg.message or ""

    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    for target in target_channels:
        try:
            await client.send_message(target, message=text, file=msg.media)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

print("🤖 Userbot is running with filters.")
client.start()
client.run_until_disconnected()
