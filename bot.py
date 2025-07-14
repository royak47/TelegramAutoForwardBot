import os
import json
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Files
ADMIN_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"
FORWARD_STATUS_FILE = "forward_status.json"
FILTER_FILE = "filters.json"
BLACKLIST_FILE = "blacklist.json"

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot._last_action = {}

# ---------- UTILITIES ----------

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

def normalize(value):
    value = value.strip()
    if value.startswith("https://t.me/+"):
        return value.split("/")[-1]
    elif value.startswith("https://t.me/"):
        return "@" + value.split("/")[-1]
    elif value.startswith("t.me/"):
        return "@" + value.split("/")[-1]
    return value

def init_files():
    if not os.path.exists(ADMIN_FILE): save_json(ADMIN_FILE, [])
    if not os.path.exists(FORWARD_STATUS_FILE): save_json(FORWARD_STATUS_FILE, {"forwarding": True})
    if not os.path.exists(SETTINGS_FILE): save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE): save_json(REPLACE_FILE, {"words": {}, "mentions": {}})
    if not os.path.exists(FILTER_FILE): save_json(FILTER_FILE, {
        "only_text": False,
        "only_image": False,
        "only_video": False,
        "only_link": False,
        "block_mentions": False
    })
    if not os.path.exists(BLACKLIST_FILE): save_json(BLACKLIST_FILE, {"words": [], "enabled": False})

def main_buttons():
    return [
        [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
        [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
        [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
        [Button.inline("🧰 Filters", b"filters"), Button.inline("📝 Edit Words", b"edit_words")],
        [Button.inline("🚫 Blacklist", b"blacklist_menu")],
        [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
    ]

# ---------- HANDLERS ----------

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id): return
    await event.respond("🤖 **Bot Control Panel:**", buttons=main_buttons())

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid): return await event.answer("Not allowed.")

    data = event.data.decode()

    if data == "settings":
        s = load_json(SETTINGS_FILE)
        f = load_json(FORWARD_STATUS_FILE)
        filters = load_json(FILTER_FILE)
        bl = load_json(BLACKLIST_FILE)
        replaces = load_json(REPLACE_FILE)
        msg = "**⚙️ Current Settings:**\n\n"
        msg += f"🔄 Forwarding: {'✅ ON' if f.get('forwarding') else '❌ OFF'}\n"
        msg += f"🚫 Blacklist: {'✅ ON' if bl.get('enabled') else '❌ OFF'}\n"
        msg += f"🙅 Block Mentions: {'✅' if filters.get('block_mentions') else '❌'}\n"
        msg += "\n📥 **Sources**:\n" + "\n".join(s.get("source_channels", [])) or "None"
        msg += "\n\n📤 **Targets**:\n" + "\n".join(s.get("target_channels", [])) or "None"
        msg += "\n\n✏️ Replacements:\n" + "\n".join([f"{k} ➔ {v}" for k,v in replaces.get("words", {}).items()])
        await event.edit(msg, parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "mentions": {}})
        await event.edit("♻️ Reset done!", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("✅ Forwarding started.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⛔ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        f = load_json(FILTER_FILE)
        await event.edit("🧰 **Toggle Filters:**", buttons=[
            [Button.inline(f"Text {'✅' if f.get('only_text') else '❌'}", b"toggle_text"),
             Button.inline(f"Image {'✅' if f.get('only_image') else '❌'}", b"toggle_image")],
            [Button.inline(f"Video {'✅' if f.get('only_video') else '❌'}", b"toggle_video"),
             Button.inline(f"Links {'✅' if f.get('only_link') else '❌'}", b"toggle_link")],
            [Button.inline(f"@Block {'✅' if f.get('block_mentions') else '❌'}", b"toggle_mentions")],
            [Button.inline("🔙 Back", b"back")]
        ])

    elif data.startswith("toggle_"):
        f = load_json(FILTER_FILE)
        key = data.replace("toggle_", "")
        if key == "mentions":
            f["block_mentions"] = not f.get("block_mentions", False)
        else:
            f[f"only_{key}"] = not f.get(f"only_{key}", False)
        save_json(FILTER_FILE, f)
        await handle_buttons(await event.edit("✅ Toggled...", buttons=[[Button.inline("🔙 Back", b"filters")]]))

    elif data == "edit_words":
        bot._last_action[uid] = "edit_words"
        await event.respond("✍️ Send replacement like: `old|new`\nUse `@mention|@your_bot_id`", parse_mode="markdown")

    elif data == "blacklist_menu":
        bl = load_json(BLACKLIST_FILE)
        await event.edit(
            "🚫 Blacklist Menu:",
            buttons=[
                [Button.inline(f"Enabled: {'✅' if bl.get('enabled') else '❌'}", b"toggle_blacklist")],
                [Button.inline("✍️ Set Words", b"set_blacklist"), Button.inline("❌ Clear", b"clear_blacklist")],
                [Button.inline("🔙 Back", b"back")]
            ]
        )

    elif data == "toggle_blacklist":
        bl = load_json(BLACKLIST_FILE)
        bl["enabled"] = not bl.get("enabled", False)
        save_json(BLACKLIST_FILE, bl)
        await event.edit("✅ Blacklist toggled.", buttons=[[Button.inline("🔙 Back", b"blacklist_menu")]])

    elif data == "set_blacklist":
        bot._last_action[uid] = "blacklist"
        await event.respond("✍️ Send comma-separated blacklist words")

    elif data == "clear_blacklist":
        save_json(BLACKLIST_FILE, {"words": [], "enabled": False})
        await event.edit("✅ Blacklist cleared.", buttons=[[Button.inline("🔙 Back", b"blacklist_menu")]])

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send @username, ID, or t.me link for `{data}`")

    elif data == "back":
        await event.edit("🔙 Main Menu:", buttons=main_buttons())

@bot.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if not is_admin(uid): return
    if uid not in bot._last_action: return

    action = bot._last_action.pop(uid)
    text = event.raw_text.strip()
    settings = load_json(SETTINGS_FILE)

    if action in ["add_source", "remove_source", "add_target", "remove_target"]:
        key = "source_channels" if "source" in action else "target_channels"
        val = normalize(text)
        if "add" in action:
            if val not in settings[key]:
                settings[key].append(val)
                await event.reply(f"✅ Added: `{val}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Already exists.")
        else:
            if val in settings[key]:
                settings[key].remove(val)
                await event.reply(f"❌ Removed: `{val}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Not found.")
        save_json(SETTINGS_FILE, settings)

    elif action == "edit_words":
        if "|" not in text:
            return await event.reply("⚠️ Use: `old|new` format")
        old, new = map(str.strip, text.split("|", 1))
        r = load_json(REPLACE_FILE)
        if old.startswith("@"): r["mentions"][old] = new
        else: r["words"][old] = new
        save_json(REPLACE_FILE, r)
        await event.reply(f"✅ Saved: `{old}` → `{new}`", parse_mode="markdown")

    elif action == "blacklist":
        words = [w.strip() for w in text.split(",") if w.strip()]
        bl = load_json(BLACKLIST_FILE)
        bl["words"] = words
        bl["enabled"] = True
        save_json(BLACKLIST_FILE, bl)
        await event.reply("✅ Blacklist updated.")

# ---------- START ----------
init_files()
print("✅ Admin Bot running...")
bot.run_until_disconnected()
