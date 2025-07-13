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

# 📦 JSON Utility
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

# ➕ Add source
@client.on(events.NewMessage(pattern="/addsource"))
async def add_source_command(event):
    last_action[event.sender_id] = "add_source"
    await event.reply("✍️ Send source @username or channel ID to add:")

# ➕ Add target
@client.on(events.NewMessage(pattern="/addtarget"))
async def add_target_command(event):
    last_action[event.sender_id] = "add_target"
    await event.reply("✍️ Send target @username or channel ID to add:")

# 🧠 All messages
@client.on(events.NewMessage())
async def handle_message(event):
    uid = event.sender_id
    text = event.text.strip() if event.text else ""

    if uid in last_action:
        action = last_action.pop(uid)
        settings = load_json(SETTINGS_FILE)

        if action == "add_source":
            if text not in settings.get("source_channels", []):
                settings.setdefault("source_channels", []).append(text)
                save_json(SETTINGS_FILE, settings)
                await event.reply(f"✅ Source added: {text}")
            else:
                await event.reply("⚠️ Source already exists.")
        elif action == "add_target":
            if text not in settings.get("target_channels", []):
                settings.setdefault("target_channels", []).append(text)
                save_json(SETTINGS_FILE, settings)
                await event.reply(f"✅ Target added: {text}")
            else:
                await event.reply("⚠️ Target already exists.")
        return

    # 🔕 Stop forwarding if disabled
    if not is_forwarding_enabled():
        return

    # 🧾 Load settings
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    filters = load_json(FILTER_FILE)
    blacklist = load_json(BLACKLIST_FILE).get("words", [])

    source_channels = settings.get("source_channels", [])
    target_channels = settings.get("target_channels", [])

    # 🧠 Check if source matched
    sender = await event.get_chat()
    chat_id = str(sender.id)
    username = f"@{getattr(sender, 'username', '')}".lower() if getattr(sender, 'username', None) else None

    if chat_id not in source_channels and (username not in [c.lower() for c in source_channels]):
        return

    msg = event.message
    text = msg.text or msg.message or ""

    # 🧹 Blacklist check
    if any(b.lower() in text.lower() for b in blacklist):
        print("🚫 Skipped due to blacklist.")
        return

    # 📌 Filters
    if filters.get("only_text") and not msg.text:
        return
    if filters.get("only_image") and not (msg.photo or (msg.file and msg.file.mime_type and msg.file.mime_type.startswith("image"))):
        return
    if filters.get("only_video") and not (msg.video or (msg.file and msg.file.mime_type and msg.file.mime_type.startswith("video"))):
        return
    if filters.get("only_link") and not any(x in text for x in ["http://", "https://"]):
        return

    # 🔁 Replacements
    for old, new in replaces.get("words", {}).items():
        text = text.replace(old, new)
    for old, new in replaces.get("links", {}).items():
        text = text.replace(old, new)

    # 🎯 Send to all target channels
    for target in target_channels:
        try:
            entity = await client.get_entity(target)
            if msg.media:
                await client.send_file(entity, file=msg.media, caption=text)
            else:
                await client.send_message(entity, message=text)
            print(f"✅ Forwarded to {target}")
        except Exception as e:
            print(f"❌ Failed to forward to {target}: {e}")

# 🚀 Start client
print("📦 Userbot started.")
client.start()
client.run_until_disconnected()
