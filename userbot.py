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

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

@client.on(events.NewMessage())
async def handler(event):
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)
    if event.chat and event.chat.username:
        if f"@{event.chat.username}" not in settings["source_channels"]:
            return

    msg = event.message

    # Replace words and links
    text = msg.message or ""
    for old, new in replaces["words"].items():
        text = text.replace(old, new)
    for old, new in replaces["links"].items():
        text = text.replace(old, new)

    for target in settings["target_channels"]:
        try:
            await client.send_message(target, file=msg.media, message=text)
        except Exception as e:
            print(f"Failed to forward to {target}: {e}")

print("📦 Userbot started.")
client.start()
client.run_until_disconnected()
