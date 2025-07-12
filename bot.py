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
FORWARD_STATUS_FILE = "forward_status.json"

bot = TelegramClient('admin_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def is_admin(user_id):
    with open(ADMIN_FILE, "r") as f:
        admins = json.load(f)
    return user_id in admins

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def init_files():
    # create forward_status.json if not exist
    if not os.path.exists(FORWARD_STATUS_FILE):
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.reply("✅ Bot is running!")

@bot.on(events.NewMessage(pattern="/forward"))
async def forward(event):
    if not is_admin(event.sender_id):
        return
    save_json(FORWARD_STATUS_FILE, {"forwarding": True})
    await event.reply("▶️ Forwarding started.")

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    if not is_admin(event.sender_id):
        return
    save_json(FORWARD_STATUS_FILE, {"forwarding": False})
    await event.reply("⏹️ Forwarding stopped.")

@bot.on(events.NewMessage(pattern="/settings"))
async def settings(event):
    if not is_admin(event.sender_id):
        return
    s = load_json(SETTINGS_FILE)
    f = load_json(FORWARD_STATUS_FILE)
    status = "✅ ON" if f.get("forwarding") else "❌ OFF"
    text = f"📦 **Settings**\n\n"
    text += f"🔄 Forwarding: {status}\n"
    text += f"📥 Sources: {', '.join(s.get('source_channels', [])) or 'None'}\n"
    text += f"📤 Targets: {', '.join(s.get('target_channels', [])) or 'None'}"
    await event.reply(text)

@bot.on(events.NewMessage(pattern="/reset"))
async def reset(event):
    if not is_admin(event.sender_id):
        return
    save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    save_json(REPLACE_FILE, {"words": {}, "links": {}})
    await event.reply("♻️ All settings have been reset.")

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
            await event.reply("⚠️ Source already exists.")
    except:
        await event.reply("❗ Usage: /setsource @channelusername")

@bot.on(events.NewMessage(pattern="/removesource"))
async def remove_source(event):
    if not is_admin(event.sender_id):
        return
    try:
        channel = event.message.text.split(" ", 1)[1]
        settings = load_json(SETTINGS_FILE)
        if channel in settings["source_channels"]:
            settings["source_channels"].remove(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"❌ Source removed: {channel}")
        else:
            await event.reply("⚠️ Source not found.")
    except:
        await event.reply("❗ Usage: /removesource @channelusername")

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
            await event.reply("⚠️ Target already exists.")
    except:
        await event.reply("❗ Usage: /settarget @channelusername")

@bot.on(events.NewMessage(pattern="/removetarget"))
async def remove_target(event):
    if not is_admin(event.sender_id):
        return
    try:
        channel = event.message.text.split(" ", 1)[1]
        settings = load_json(SETTINGS_FILE)
        if channel in settings["target_channels"]:
            settings["target_channels"].remove(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"❌ Target removed: {channel}")
        else:
            await event.reply("⚠️ Target not found.")
    except:
        await event.reply("❗ Usage: /removetarget @channelusername")

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

# Initialize on first run
init_files()

print("🤖 Admin bot started.")
bot.run_until_disconnected()
