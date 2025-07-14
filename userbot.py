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

# ---------- HANDLER ----------

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    blacklist_data = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)

    sender = await event.get_chat()
    sender_id = str(sender.id)
    sender_username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else ""
    sender_invite = getattr(sender, 'invite_hash', None)
    sender_inputs = [sender_id, sender_username, sender_invite]

    # Find matching targets for this source
    matched_targets = []
    for pair in settings.get("pairs", []):
        if pair["source"] in sender_inputs:
            matched_targets.append(pair["target"])

    if not matched_targets:
        return  # no valid source → skip

    msg = event.message
    text = msg.message or ""

    # Filters
    if filters.get("block_mentions") and "@" in text:
        return

    if blacklist_data.get("enabled"):
        for word in blacklist_data.get("words", []):
            text = text.replace(word, "")

    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("mentions", {}).items():
        text = text.replace(old, new)

    if filters.get("only_text") and not msg.media:
        pass
    elif filters.get("only_image") and not msg.photo:
        return
    elif filters.get("only_video") and not msg.video:
        return
    elif filters.get("only_link") and ("http" not in text and "www" not in text):
        return

    for target in matched_targets:
        try:
            await client.send_message(target, file=msg.media, message=text)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

# ---------- START ----------

print("🚀 Userbot started.")
client.start()
client.run_until_disconnected()
