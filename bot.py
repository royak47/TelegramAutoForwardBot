import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"

bot = TelegramClient('admin_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Load admin IDs
with open(ADMIN_FILE, "r") as f:
    ADMINS = json.load(f)

def is_admin(user_id):
    return user_id in ADMINS

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.reply("✅ Bot is running!")

@bot.on(events.NewMessage(pattern="/setsource"))
async def set_source(event):
    if not is_admin(event.sender_id):
        return
    try:
        channel = event.message.text.split(" ", 1)[1]
        settings = load_json(SETTINGS_FILE)
        if channel not in settings["source_channels"]:
            settings["source_channels"].append(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"✅ Source channel added: {channel}")
        else:
            await event.reply("⚠️ Already exists.")
    except:
        await event.reply("❗ Usage: /setsource @channelusername")

@bot.on(events.NewMessage(pattern="/settarget"))
async def set_target(event):
    if not is_admin(event.sender_id):
        return
    try:
        channel = event.message.text.split(" ", 1)[1]
        settings = load_json(SETTINGS_FILE)
        if channel not in settings["target_channels"]:
            settings["target_channels"].append(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"✅ Target channel added: {channel}")
        else:
            await event.reply("⚠️ Already exists.")
    except:
        await event.reply("❗ Usage: /settarget @channelusername")

@bot.on(events.NewMessage(pattern="/addword"))
async def add_word(event):
    if not is_admin(event.sender_id):
        return
    try:
        old, new = event.message.text.split(" ", 2)[1:]
        data = load_json(REPLACE_FILE)
        data["words"][old] = new
        save_json(REPLACE_FILE, data)
        await event.reply(f"✅ Word replace rule added:\n{old} → {new}")
    except:
        await event.reply("❗ Usage: /addword old new")

@bot.on(events.NewMessage(pattern="/addlink"))
async def add_link(event):
    if not is_admin(event.sender_id):
        return
    try:
        old, new = event.message.text.split(" ", 2)[1:]
        data = load_json(REPLACE_FILE)
        data["links"][old] = new
        save_json(REPLACE_FILE, data)
        await event.reply(f"✅ Link replace rule added:\n{old} → {new}")
    except:
        await event.reply("❗ Usage: /addlink oldlink newlink")

print("🤖 Admin bot started.")
bot.run_until_disconnected()
