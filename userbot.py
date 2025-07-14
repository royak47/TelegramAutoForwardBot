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

def match_source_identifier(sender):
    """
    Return list of identifiers that could match the source:
    - Chat ID (e.g., -100123...)
    - @username
    - invite link (https://t.me/+abc)
    """
    identifiers = []
    if hasattr(sender, "id"):
        identifiers.append(str(sender.id))
    if hasattr(sender, "username") and sender.username:
        identifiers.append("@" + sender.username.lower())
    if hasattr(sender, "invite") and sender.invite and hasattr(sender.invite, "link"):
        identifiers.append(sender.invite.link)
    return identifiers

def normalize(source):
    source = source.strip()
    if source.startswith("https://t.me/+"):
        return source
    elif source.startswith("https://t.me/"):
        return "@" + source.split("/")[-1]
    elif source.startswith("t.me/+"):
        return "https://" + source
    elif source.startswith("t.me/"):
        return "@" + source.split("/")[-1]
    return source

# ---------- MAIN FORWARD HANDLER ----------

@client.on(events.NewMessage())
async def forward_handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    blacklist_data = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)

    pairs = settings.get("pairs", [])
    if not pairs:
        return

    sender = await event.get_chat()
    identifiers = match_source_identifier(sender)

    # Match source
    matched_targets = []
    for pair in pairs:
        source = normalize(pair.get("source", ""))
        if source in identifiers:
            matched_targets.append(pair.get("target"))

    if not matched_targets:
        return  # No match

    msg = event.message
    text = msg.message or ""

    # Apply filters
    if filters.get("only_text") and not msg.media:
        pass
    elif filters.get("only_image") and not msg.photo:
        return
    elif filters.get("only_video") and not msg.video:
        return
    elif filters.get("only_link") and ("http" not in text and "www" not in text):
        return
    elif filters.get("block_mentions") and "@" in text:
        return

    # Apply blacklist
    if blacklist_data.get("enabled"):
        for word in blacklist_data.get("words", []):
            if word:
                text = text.replace(word, "")

    # Apply replacements
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("mentions", {}).items():
        text = text.replace(old, new)

    # Send to matched target(s)
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
