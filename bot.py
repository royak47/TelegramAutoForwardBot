import os
import json
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot._last_action = {}

SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"
BLACKLIST_FILE = "blacklist.json"
FILTER_FILE = "filters.json"
FORWARD_STATUS_FILE = "forward_status.json"
ADMIN_FILE = "admins.json"

# -------------------------- UTILS --------------------------

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def normalize(value):
    value = value.strip()
    if value.startswith("https://t.me/"):
        return "@" + value.split("/")[-1]
    elif value.startswith("t.me/"):
        return "@" + value.split("/")[-1]
    return value

def split_buttons(buttons, cols=2):
    return [buttons[i:i+cols] for i in range(0, len(buttons), cols)]

def is_admin(uid):
    try:
        return uid in load_json(ADMIN_FILE)
    except:
        return False

def init_files():
    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE):
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "mentions": {}})
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"words": [], "enabled": True})
    if not os.path.exists(FILTER_FILE):
        save_json(FILTER_FILE, {
            "only_text": False,
            "only_image": False,
            "only_video": False,
            "only_link": False,
            "replace_enabled": True
        })
    if not os.path.exists(FORWARD_STATUS_FILE):
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})

# -------------------------- MAIN MENU --------------------------

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return

    await event.delete()
    await event.respond("🤖 **Bot is active! Choose an action:**", buttons=[
        [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
        [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
        [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
        [Button.inline("✏️ Replace Words", b"replace_words"), Button.inline("🔁 Replace Mentions", b"replace_mentions")],
        [Button.inline("🚫 Blacklist Words", b"blacklist_words"), Button.inline("🧰 Filters", b"filters")],
        [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
    ])

# -------------------------- CALLBACKS --------------------------

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid):
        return await event.answer("Not allowed.")

    data = event.data.decode()
    settings = load_json(SETTINGS_FILE)
    filters = load_json(FILTER_FILE)
    forward_status = load_json(FORWARD_STATUS_FILE)
    blacklist = load_json(BLACKLIST_FILE)
    replaces = load_json(REPLACE_FILE)

    # Settings Panel
    if data == "settings":
        msg = "📦 **Current Settings:**\n\n"
        msg += f"🔄 Forwarding: {'✅ ON' if forward_status['forwarding'] else '❌ OFF'}\n"
        msg += f"🔤 Replace Words: {'✅' if filters.get('replace_enabled') else '❌'}\n"
        msg += f"🚫 Blacklist: {'✅' if blacklist.get('enabled') else '❌'}\n"
        msg += "\n📥 Sources:\n" + "\n".join(settings["source_channels"]) or "None"
        msg += "\n\n📤 Targets:\n" + "\n".join(settings["target_channels"]) or "None"
        await event.edit(msg, buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "mentions": {}})
        save_json(BLACKLIST_FILE, {"words": [], "enabled": True})
        await event.edit("♻️ All settings reset.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "forward":
        forward_status["forwarding"] = True
        save_json(FORWARD_STATUS_FILE, forward_status)
        await event.edit("▶️ Forwarding enabled.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "stop":
        forward_status["forwarding"] = False
        save_json(FORWARD_STATUS_FILE, forward_status)
        await event.edit("⏹ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        await event.edit("🧰 Toggle Filters:", buttons=[
            [Button.inline(f"📝 Text: {'✅' if filters['only_text'] else '❌'}", b"toggle_text"),
             Button.inline(f"🖼 Image: {'✅' if filters['only_image'] else '❌'}", b"toggle_image")],
            [Button.inline(f"🎥 Video: {'✅' if filters['only_video'] else '❌'}", b"toggle_video"),
             Button.inline(f"🔗 Link: {'✅' if filters['only_link'] else '❌'}", b"toggle_link")],
            [Button.inline(f"🔤 Replacements: {'✅' if filters.get('replace_enabled') else '❌'}", b"toggle_replace"),
             Button.inline(f"🚫 Blacklist: {'✅' if blacklist.get('enabled') else '❌'}", b"toggle_blacklist")],
            [Button.inline("🔙 Back", b"back")]
        ])

    elif data.startswith("toggle_"):
        key = data.split("_", 1)[1]
        if key == "blacklist":
            blacklist["enabled"] = not blacklist.get("enabled")
            save_json(BLACKLIST_FILE, blacklist)
        else:
            filters_key = "replace_enabled" if key == "replace" else f"only_{key}"
            filters[filters_key] = not filters.get(filters_key, False)
            save_json(FILTER_FILE, filters)
        await handle_buttons(await event.edit("Updating..."))

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send channel @username or ID to `{data}`")

    elif data == "replace_words":
        bot._last_action[uid] = "replace_words"
        await event.respond("✍️ Send replace pair as: `old|new`")

    elif data == "replace_mentions":
        bot._last_action[uid] = "replace_mentions"
        await event.respond("✍️ Send mention replace: `@mention1|@mention2`")

    elif data == "blacklist_words":
        bot._last_action[uid] = "blacklist_words"
        await event.respond("✍️ Send words (comma-separated) to blacklist")

    elif data == "back":
        await start(event)

# -------------------------- TEXT INPUT --------------------------

@bot.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if not is_admin(uid) or uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    text = event.text.strip()
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)

    if action in ["add_source", "remove_source", "add_target", "remove_target"]:
        key = "source_channels" if "source" in action else "target_channels"
        norm = normalize(text)
        if "add" in action:
            if norm not in settings[key]:
                settings[key].append(norm)
                await event.reply(f"✅ Added: `{norm}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Already exists.")
        else:
            if norm in settings[key]:
                settings[key].remove(norm)
                await event.reply(f"❌ Removed: `{norm}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Not found.")
        save_json(SETTINGS_FILE, settings)

    elif action == "replace_words":
        try:
            old, new = map(str.strip, text.split("|"))
            replaces["words"][old] = new
            save_json(REPLACE_FILE, replaces)
            await event.reply(f"✅ Word replaced `{old}` → `{new}`", parse_mode="markdown")
        except:
            await event.reply("❗ Use `old|new` format")

    elif action == "replace_mentions":
        try:
            old, new = map(str.strip, text.split("|"))
            if "mentions" not in replaces:
                replaces["mentions"] = {}
            replaces["mentions"][old] = new
            save_json(REPLACE_FILE, replaces)
            await event.reply(f"✅ Mention replaced `{old}` → `{new}`", parse_mode="markdown")
        except:
            await event.reply("❗ Use `@old|@new` format")

    elif action == "blacklist_words":
        bl = [w.strip() for w in text.split(",") if w.strip()]
        save_json(BLACKLIST_FILE, {"words": bl, "enabled": True})
        await event.reply(f"✅ Blacklist updated:\n{', '.join(bl)}")

# --------------------------

init_files()
print("✅ Admin Bot running...")
bot.run_until_disconnected()
