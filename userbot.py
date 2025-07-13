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
BLACKLIST_FILE = "blacklist.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
last_action = {}

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def is_forwarding_enabled():
    return load_json(FORWARD_STATUS_FILE).get("forwarding", True)

@client.on(events.NewMessage())
async def handle_message(event):
    if not is_forwarding_enabled():
        return

    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    filters = load_json(FILTER_FILE)
    blacklist = load_json(BLACKLIST_FILE).get("words", [])

    source_channels = settings.get("source_channels", [])
    target_channels = settings.get("target_channels", [])

    sender = await event.get_chat()
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None

    matched = False
    for src in source_channels:
        if src.startswith("-100") and str(chat_id) == src:
            matched = True
        elif username and src.lower() == username:
            matched = True

    if not matched:
        return

    msg = event.message
    text = msg.text or msg.message or ""

    print(f"📥 New message from {username or chat_id}")

    # Check blacklist
    if any(b.lower() in text.lower() for b in blacklist):
        print("🚫 Blocked due to blacklist")
        return

    # Check filters
    if filters.get("only_text") and not msg.text:
        return
    if filters.get("only_image") and not (msg.photo or (msg.file and msg.file.mime_type and msg.file.mime_type.startswith("image"))):
        return
    if filters.get("only_video") and not (msg.video or (msg.file and msg.file.mime_type and msg.file.mime_type.startswith("video"))):
        return
    if filters.get("only_link") and not any(x in text for x in ["http://", "https://"]):
        return

    # Apply replacements
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    # Send to targets
    for target in target_channels:
        try:
            print(f"➡️ Forwarding to {target}")
            entity = await client.get_entity(target)
            if msg.media:
                await client.send_file(entity, file=msg.media, caption=text)
            else:
                await client.send_message(entity, message=text)
            print(f"✅ Sent to {target}")
        except Exception as e:
            print(f"❌ Failed to send to {target}: {e}")

print("🚀 Userbot running...")
client.start()
client.run_until_disconnected()
