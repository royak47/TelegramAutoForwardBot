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
FORWARD_STATUS_FILE = "forward_status.json"
BLOCKLIST_FILE = "blocklist.json"
ADMIN_FILE = "admins.json"

# Load configs
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def is_admin(user_id):
    admins = load_json(ADMIN_FILE)
    return user_id in admins

settings = load_json(SETTINGS_FILE)
replacements = load_json(REPLACE_FILE)
blocklist = load_json(BLOCKLIST_FILE)
forward_status = load_json(FORWARD_STATUS_FILE)

if "edit_sync" not in forward_status:
    forward_status["edit_sync"] = True
if "delete_sync" not in forward_status:
    forward_status["delete_sync"] = True
if "sticker_replace" not in forward_status:
    forward_status["sticker_replace"] = False
save_json(FORWARD_STATUS_FILE, forward_status)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def process_message(event, is_edit=False):
    forward_status = load_json(FORWARD_STATUS_FILE)
    if not forward_status.get("forwarding", True):
        return

    if is_edit and not forward_status.get("edit_sync", True):
        return

    if event.chat_id not in settings.get("source_ids", []):
        return

    if not event.message:
        return

    text = event.message.message or ""

    # Blocked content check
    if text in blocklist:
        return

    # Word replacement
    for old, new in replacements.get("words", {}).items():
        text = text.replace(old, new)

    # Link replacement
    for old, new in replacements.get("links", {}).items():
        text = text.replace(old, new)

    # Replace stickers if enabled
    send_kwargs = {}
    if event.message.sticker and forward_status.get("sticker_replace"):
        text = "[🔥]"
    else:
        send_kwargs["file"] = event.message.media if event.message.media else None

    for target in settings.get("target_ids", []):
        try:
            if is_edit:
                await client.edit_message(target, event.message.id, text)
            else:
                await client.send_message(target, text, **send_kwargs)
        except Exception as e:
            print(f"Error forwarding/editing to {target}: {e}")

@client.on(events.NewMessage())
async def handler(event):
    await process_message(event)

@client.on(events.MessageEdited())
async def edit_handler(event):
    forward_status = load_json(FORWARD_STATUS_FILE)
    if forward_status.get("edit_sync", True):
        await process_message(event, is_edit=True)

@client.on(events.MessageDeleted())
async def delete_handler(event):
    forward_status = load_json(FORWARD_STATUS_FILE)
    if not forward_status.get("delete_sync", True):
        return

    if event.chat_id not in settings.get("source_ids", []):
        return

    for msg_id in event.deleted_ids:
        for target in settings.get("target_ids", []):
            try:
                await client.delete_messages(target, msg_id)
            except Exception as e:
                print(f"Error deleting in {target}: {e}")

@client.on(events.NewMessage(pattern="/(edit_sync|delete_sync|sticker_replace) ?(on|off)?"))
async def toggle_features(event):
    if not is_admin(event.sender_id):
        return
    forward_status = load_json(FORWARD_STATUS_FILE)
    args = event.message.text.split()
    if len(args) == 1:
        status_text = f"\n🔧 Current Toggles:\n"
        for k in ["edit_sync", "delete_sync", "sticker_replace"]:
            v = forward_status.get(k, False)
            status_text += f"{k}: {'✅ ON' if v else '❌ OFF'}\n"
        await event.reply(status_text)
        return

    feature = args[0].lstrip("/")
    action = args[1].lower()
    if feature in forward_status:
        forward_status[feature] = True if action == "on" else False
        save_json(FORWARD_STATUS_FILE, forward_status)
        await event.reply(f"🔄 {feature} set to {action.upper()} ✅")
    else:
        await event.reply("❗ Invalid feature")

print("📦 Userbot started.")
client.start()
client.run_until_disconnected()
