import os
import json
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
FILTER_FILE = "filters.json"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def normalize_sender(sender):
    if sender.username:
        return f"@{sender.username}".lower()
    if hasattr(sender, "id"):
        return str(sender.id)
    if hasattr(sender, "invite_hash"):
        return f"https://t.me/+{sender.invite_hash}"
    return ""

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    blacklist_data = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)

    sender = await event.get_chat()
    sender_id = normalize_sender(sender)

    # Find targets only for matching source
    matched_targets = []
    for pair in settings.get("pairs", []):
        source = pair.get("source", "").strip().lower()
        if source == sender_id:
            matched_targets.append(pair.get("target"))

    if not matched_targets:
        return  # No matching source → skip

    msg = event.message
    text = msg.message or ""

    # @block mentions
    if filters.get("block_mentions") and "@" in text:
        return

    # Apply blacklist (partial block)
    if blacklist_data.get("enabled"):
        for word in blacklist_data.get("words", []):
            if word:
                text = text.replace(word, "")

    # Replacements
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("mentions", {}).items():
        text = text.replace(old, new)

    # Filters
    if filters.get("only_text") and msg.media:
        return
    if filters.get("only_image") and not msg.photo:
        return
    if filters.get("only_video") and not msg.video:
        return
    if filters.get("only_link") and ("http" not in text and "www" not in text):
        return

    # Forward to matched targets
    for target in matched_targets:
        try:
            await client.send_message(target, file=msg.media, message=text)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
