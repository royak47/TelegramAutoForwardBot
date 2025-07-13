import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"
FORWARD_STATUS_FILE = "forward_status.json"

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Utility Functions
def is_admin(user_id):
    try:
        with open(ADMIN_FILE) as f:
            return user_id in json.load(f)
    except:
        return False

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file) as f:
        return json.load(f)

def init_files():
    if not os.path.exists(FORWARD_STATUS_FILE):
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE):
        save_json(REPLACE_FILE, {"words": {}, "links": {}})

# /start command with inline buttons
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "🤖 **Bot is active!**\nChoose an action below:",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
            [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("▶️ Start Forwarding", b"forward"), Button.inline("⏹ Stop", b"stop")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    if not is_admin(event.sender_id):
        await event.answer("Not authorized.")
        return
    data = event.data.decode()

    if data == "settings":
        s = load_json(SETTINGS_FILE)
        f = load_json(FORWARD_STATUS_FILE)
        text = "📦 **Settings**\n\n"
        text += f"🔄 Forwarding: {'✅ ON' if f.get('forwarding') else '❌ OFF'}\n"
        text += f"📥 Sources:\n" + "\n".join(s.get("source_channels", [])) or "None"
        text += f"\n📤 Targets:\n" + "\n".join(s.get("target_channels", [])) or "None"
        await event.edit(text)

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "links": {}})
        await event.edit("♻️ All settings have been reset.")

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding started.")

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹️ Forwarding stopped.")

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        await event.respond(f"✍️ Please send the channel **@username** or **ID** for `{data}`:")
        bot._last_action[event.sender_id] = data  # temp state storage

# Handle dynamic channel input
bot._last_action = {}

@bot.on(events.NewMessage)
async def handle_channel_input(event):
    uid = event.sender_id
    if not is_admin(uid):
        return

    if uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    channel = event.text.strip()
    settings = load_json(SETTINGS_FILE)

    if action == "add_source":
        if channel not in settings["source_channels"]:
            settings["source_channels"].append(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"✅ Source added: {channel}")
        else:
            await event.reply("⚠️ Already in source list.")
    elif action == "remove_source":
        if channel in settings["source_channels"]:
            settings["source_channels"].remove(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"❌ Source removed: {channel}")
        else:
            await event.reply("⚠️ Not found in source list.")
    elif action == "add_target":
        if channel not in settings["target_channels"]:
            settings["target_channels"].append(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"✅ Target added: {channel}")
        else:
            await event.reply("⚠️ Already in target list.")
    elif action == "remove_target":
        if channel in settings["target_channels"]:
            settings["target_channels"].remove(channel)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"❌ Target removed: {channel}")
        else:
            await event.reply("⚠️ Not found in target list.")

# Word/Link replacement commands (same as your version)
@bot.on(events.NewMessage(pattern="/addword"))
async def add_word(event):
    if not is_admin(event.sender_id):
        return
    try:
        old, new = event.message.text.split(" ", 2)[1:]
        data = load_json(REPLACE_FILE)
        data["words"][old] = new
        save_json(REPLACE_FILE, data)
        await event.reply(f"📝 Word replace rule:\n`{old}` → `{new}`")
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
        await event.reply(f"🔗 Link replace rule:\n`{old}` → `{new}`")
    except:
        await event.reply("❗ Usage: /addlink oldlink newlink")

# Init & Run
init_files()
print("✅ Admin Bot Started.")
bot.run_until_disconnected()
