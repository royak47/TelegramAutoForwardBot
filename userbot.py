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

# ------------------- Utilities -------------------

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def normalize_source(val):
    val = val.strip()
    if val.startswith("https://t.me/+"):
        return val  # full private invite
    elif val.startswith("https://t.me/"):
        return "@" + val.split("/")[-1]
    elif val.startswith("t.me/+"):
        return "https://" + val
    elif val.startswith("t.me/"):
        return "@" + val.split("/")[-1]
    return val

def match_source(sender):
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else ""
    invite_link = getattr(sender, 'exported_invite', None)
    return [chat_id, username, invite_link]

# ------------------- Handler -------------------

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    blacklist_data = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)

    pairs = settings.get("pairs", [])
    sender = await event.get_chat()
    sources = match_source(sender)

    matched_targets = []
    for pair in pairs:
        norm_source = normalize_source(pair["source"])
        if norm_source in sources:
            matched_targets.append(pair["target"])

    if not matched_targets:
        return

    msg = event.message
    text = msg.message or ""

    # Filter: block @mentions
    if filters.get("block_mentions") and "@" in text:
        return

    # Filter types
    if filters.get("only_text") and not msg.media:
        pass
    elif filters.get("only_image") and not msg.photo:
        return
    elif filters.get("only_video") and not msg.video:
        return
    elif filters.get("only_link") and not ("http" in text or "www" in text):
        return

    # Blacklist (remove words, not block full msg)
    if blacklist_data.get("enabled"):
        for word in blacklist_data.get("words", []):
            text = text.replace(word, "")

    # Replacements
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("mentions", {}).items():
        text = text.replace(old, new)

    # Forward to matched targets
    for target in matched_targets:
        try:
            await client.send_message(target, file=msg.media, message=text)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

# ------------------- Start -------------------

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
