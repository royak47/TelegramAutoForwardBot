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
    if getattr(sender, "username", None):
        return f"@{sender.username.lower()}"
    if str(sender.id).startswith("-100"):
        return str(sender.id)
    if getattr(sender, "invite_hash", None):
        return f"https://t.me/+{sender.invite_hash}"
    return str(sender.id)

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    blacklist_data = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)

    pairs = settings.get("pairs", [])

    sender = await event.get_chat()
    source_key = normalize_sender(sender)

    # Match pairs
    matched_targets = [pair["target"] for pair in pairs if pair["source"].lower() == source_key.lower()]
    if not matched_targets:
        return

    msg = event.message
    text = msg.message or ""

    # Block mentions
    if filters.get("block_mentions") and "@" in text:
        return

    # Apply blacklist (remove words)
    if blacklist_data.get("enabled"):
        for word in blacklist_data.get("words", []):
            text = text.replace(word, "")

    # Word and mention replacements
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

    # Forward only to matched target(s)
    for target in matched_targets:
        try:
            await client.send_message(target, message=text, file=msg.media)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
