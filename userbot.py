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

def normalize(val):
    val = val.strip()
    if val.startswith("https://t.me/+"):
        return val
    elif val.startswith("https://t.me/"):
        return "@" + val.split("/")[-1]
    elif val.startswith("t.me/+"):
        return "https://" + val
    elif val.startswith("t.me/"):
        return "@" + val.split("/")[-1]
    return val

def get_matching_targets(sender):
    settings = load_json(SETTINGS_FILE)
    pairs = settings.get("pairs", [])
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else ""
    invite_link = getattr(sender, 'invite_link', None) or ""

    targets = []
    for pair in pairs:
        src = normalize(pair["source"])
        if src in [chat_id, username, invite_link]:
            targets.append(pair["target"])
    return targets

# ---------- HANDLER ----------

@client.on(events.NewMessage())
async def handler(event):
    replaces = load_json(REPLACE_FILE)
    blacklist_data = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)

    sender = await event.get_chat()
    targets = get_matching_targets(sender)

    if not targets:
        return

    msg = event.message
    text = msg.message or ""

    # BLOCK @MENTIONS
    if filters.get("block_mentions") and "@" in text:
        return

    # BLACKLIST FILTER
    if blacklist_data.get("enabled"):
        for word in blacklist_data.get("words", []):
            if word:
                text = text.replace(word, "")

    # REPLACEMENTS
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("mentions", {}).items():
        text = text.replace(old, new)

    # FILTERS
    if filters.get("only_text") and not msg.media:
        pass
    elif filters.get("only_image") and not msg.photo:
        return
    elif filters.get("only_video") and not msg.video:
        return
    elif filters.get("only_link") and ("http" not in text and "www" not in text):
        return

    for target in targets:
        try:
            await client.send_message(target, file=msg.media, message=text)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

# ---------- START ----------

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
