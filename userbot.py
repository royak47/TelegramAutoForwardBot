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

# ---------- UTILITIES ----------

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def normalize(value):
    value = value.strip()
    if value.startswith("https://t.me/+"):
        return value  # full invite
    elif value.startswith("https://t.me/"):
        return "@" + value.split("/")[-1]
    elif value.startswith("t.me/+"):
        return "https://" + value
    elif value.startswith("t.me/"):
        return "@" + value.split("/")[-1]
    return value

def match_source(sender):
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else ""
    invite = getattr(sender, 'invite_hash', None)
    all_ids = {chat_id, username, invite}
    return list(filter(None, all_ids))

# ---------- HANDLER ----------

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    blacklist_data = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)

    sender = await event.get_chat()
    source_keys = match_source(sender)

    # Get matched pairs for this source
    valid_targets = []
    for p in settings.get("pairs", []):
        if normalize(p["source"]) in source_keys:
            valid_targets.append(p["target"])

    if not valid_targets:
        return

    msg = event.message
    text = msg.message or ""

    # 🛑 Block @mentions
    if filters.get("block_mentions") and "@" in text:
        return

    # 🧹 Apply blacklist (clean only, not skip)
    if blacklist_data.get("enabled"):
        for word in blacklist_data.get("words", []):
            text = text.replace(word, "")

    # 🔁 Replace words & mentions
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("mentions", {}).items():
        text = text.replace(old, new)

    # 🎯 Apply media filters
    if filters.get("only_text") and msg.media:
        return
    if filters.get("only_image") and not msg.photo:
        return
    if filters.get("only_video") and not msg.video:
        return
    if filters.get("only_link") and ("http" not in text and "www" not in text):
        return

    # 📤 Forward to valid targets
    for target in valid_targets:
        try:
            await client.send_message(target, message=text, file=msg.media)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

# ---------- START ----------

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
