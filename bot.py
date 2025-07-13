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

# Session memory to hold user input context
bot._last_action = {}

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

# Start command
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "🤖 **Bot is active!** Choose an action:",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
            [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("✍️ Add Word", b"add_word"), Button.inline("🔗 Add Link", b"add_link")],
            [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
        ]
    )

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    if not is_admin(event.sender_id):
        await event.answer("Not authorized.")
        return
    data = event.data.decode()
    uid = event.sender_id

    if data == "settings":
        s = load_json(SETTINGS_FILE)
        f = load_json(FORWARD_STATUS_FILE)
        w = load_json(REPLACE_FILE)
        text = "📦 **Settings**\n\n"
        text += f"🔄 Forwarding: {'✅ ON' if f.get('forwarding') else '❌ OFF'}\n"
        text += f"📥 Sources:\n" + "\n".join(s.get("source_channels", [])) or "None"
        text += f"\n\n📤 Targets:\n" + "\n".join(s.get("target_channels", [])) or "None"
        text += f"\n\n📝 Word Replacements:\n" + "\n".join([f"`{k}` → `{v}`" for k, v in w.get("words", {}).items()]) or "None"
        text += f"\n\n🔗 Link Replacements:\n" + "\n".join([f"`{k}` → `{v}`" for k, v in w.get("links", {}).items()]) or "None"
        await event.edit(text, parse_mode="markdown")

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

    elif data in ["add_source", "remove_source", "add_target", "remove_target", "add_word", "add_link"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send input for **{data}**\n\n• Channels = `@username`, `-100...`, or `https://t.me/c/ID/msg`\n• Word = `old new`\n• Link = `oldlink newlink`", parse_mode="markdown")

@bot.on(events.NewMessage)
async def handle_input(event):
    uid = event.sender_id
    if not is_admin(uid):
        return
    if uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    msg = event.text.strip()
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)

    # Handle source/target input
    if action in ["add_source", "remove_source", "add_target", "remove_target"]:
        field = "source_channels" if "source" in action else "target_channels"
        channels = settings.get(field, [])

        if action.startswith("add_"):
            if msg not in channels:
                channels.append(msg)
                settings[field] = channels
                save_json(SETTINGS_FILE, settings)
                await event.reply(f"✅ Added to `{field}`: `{msg}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Already added.")
        else:
            if msg in channels:
                channels.remove(msg)
                settings[field] = channels
                save_json(SETTINGS_FILE, settings)
                await event.reply(f"❌ Removed from `{field}`: `{msg}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Not found.")

    # Handle word/link replacement
    elif action == "add_word":
        try:
            old, new = msg.split(" ", 1)
            replaces["words"][old] = new
            save_json(REPLACE_FILE, replaces)
            await event.reply(f"📝 Word replace rule added:\n`{old}` → `{new}`", parse_mode="markdown")
        except:
            await event.reply("❗ Usage: `old new`", parse_mode="markdown")

    elif action == "add_link":
        try:
            old, new = msg.split(" ", 1)
            replaces["links"][old] = new
            save_json(REPLACE_FILE, replaces)
            await event.reply(f"🔗 Link replace rule added:\n`{old}` → `{new}`", parse_mode="markdown")
        except:
            await event.reply("❗ Usage: `oldlink newlink`", parse_mode="markdown")

# Init
init_files()
print("✅ Admin Bot Started.")
bot.run_until_disconnected()
