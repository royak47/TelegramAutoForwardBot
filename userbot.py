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

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)


def is_forwarding_enabled():
    return load_json(FORWARD_STATUS_FILE).get("forwarding", True)


@client.on(events.NewMessage())
async def handle_message(event):
    if not is_forwarding_enabled():
        print("🚫 Forwarding is OFF")
        return

    settings = load_json(SETTINGS_FILE)
    source_channels = settings.get("source_channels", [])
    target_channels = settings.get("target_channels", [])

    sender = await event.get_chat()
    chat_id = str(sender.id)

    print(f"📨 Incoming from: {chat_id}")

    if chat_id not in source_channels:
        print("⚠️ Not in source_channels, skipping.")
        return

    for target in target_channels:
        try:
            print(f"⏩ Sending to {target}")
            await client.send_message(entity=target, message=event.message.message or "", file=event.message.media)
            print(f"✅ Sent to {target}")
        except Exception as e:
            print(f"❌ Failed to send to {target}: {e}")


print("🚀 Userbot running...")
client.start()
client.run_until_disconnected()
