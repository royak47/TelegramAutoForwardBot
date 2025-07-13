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
REPLACE_FILE = "replacements.json"
FILTER_FILE = "filters.json"
BLACKLIST_FILE = "blacklist.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def is_forwarding_enabled():
    return load_json(FORWARD_STATUS_FILE).get("forwarding", True)

@client.on(events.NewMessage())
async def handle_message(event):
    if not is_forwarding_enabled():
        return

    settings = load_json(SETTINGS_FILE)
    source_channels = settings.get("source_channels", [])
    target_channels = settings.get("target_channels", [])

    replaces = load_json(REPLACE_FILE)
    filters = load_json(FILTER_FILE)
    blacklist = load_json(BLACKLIST_FILE).get("words", [])

    sender = await event.get_chat()
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None
    link = f"t.me/{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None

    source_channels_normalized = [s.lower() for s in source_channels]

    if (
        chat_id not in source_channels_normalized and
        username not in source_channels_normalized and
        link not in source_channels_normalized
    ):
        print(f"⚠️ Message ignored from: {chat_id} {username}")
        return

    msg = event.message
    text = msg.message or ""

    if any(b in text for b in blacklist):
        print("🚫 Skipped due to blacklist word.")
        return

    if filters.get("only_text") and not msg.text:
        return
    if filters.get("only_image") and not (msg.photo or (msg.file and msg.file.mime_type.startswith("image"))):
        return
    if filters.get("only_video") and not (msg.video or (msg.file and msg.file.mime_type.startswith("video"))):
        return
    if filters.get("only_link") and not any(x in text for x in ["http://", "https://"]):
        return

    # Replace words/links
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

print("🚀 Userbot running...")
client.start()
client.run_until_disconnected()
