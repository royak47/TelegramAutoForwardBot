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

def normalize_id(chat_id):
    """Ensure channel ID has -100 prefix if it's an integer."""
    try:
        cid = int(chat_id)
        return str(cid) if str(cid).startswith("-100") else f"-100{cid}"
    except:
        return chat_id.lower().strip()

def normalize_all(channels):
    """Normalize channel usernames and IDs."""
    norm = []
    for c in channels:
        c = str(c).strip()
        if c.startswith("@"):
            norm.append(c.lower())
        elif c.startswith("t.me/"):
            norm.append(c.lower())
        elif c.isdigit() or (c.startswith("-100") and c[4:].isdigit()):
            norm.append(normalize_id(c))
    return norm

@client.on(events.NewMessage())
async def handle_message(event):
    if not is_forwarding_enabled():
        return

    settings = load_json(SETTINGS_FILE)
    source_channels = normalize_all(settings.get("source_channels", []))
    target_channels = normalize_all(settings.get("target_channels", []))

    replaces = load_json(REPLACE_FILE)
    filters = load_json(FILTER_FILE)
    blacklist = load_json(BLACKLIST_FILE).get("words", [])

    sender = await event.get_chat()
    chat_id = normalize_id(str(sender.id))
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else ""
    link = f"t.me/{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else ""

    if chat_id not in source_channels and username not in source_channels and link not in source_channels:
        print(f"⚠️ Message ignored from: {chat_id} {username}")
        return

    msg = event.message
    text = msg.message or ""

    if any(b in text for b in blacklist):
        print("🚫 Skipped due to blacklist.")
        return

    if filters.get("only_text") and not msg.text:
        return
    if filters.get("only_image") and not (msg.photo or (msg.file and msg.file.mime_type and msg.file.mime_type.startswith("image"))):
        return
    if filters.get("only_video") and not (msg.video or (msg.file and msg.file.mime_type and msg.file.mime_type.startswith("video"))):
        return
    if filters.get("only_link") and not any(x in text for x in ["http://", "https://"]):
        return

    # Replace text
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

print("🚀 Userbot running...")
client.start()
client.run_until_disconnected()
