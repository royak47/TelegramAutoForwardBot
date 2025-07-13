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
FILTER_FILE = "filters.json"
BLACKLIST_FILE = "blacklist.json"

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot._last_action = {}

# Utils
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

def normalize(value: str) -> str:
    value = value.strip()
    if value.startswith("https://t.me/"):
        return "@" + value.split("/")[-1]
    elif value.startswith("t.me/"):
        return "@" + value.split("/")[-1]
    return value

def init_files():
    if not os.path.exists(FORWARD_STATUS_FILE):
        save_json(FORWARD_STATUS_FILE, {"forwarding": True, "blacklist_enabled": True})
    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE):
        save_json(REPLACE_FILE, {"words": {}, "links": {}})
    if not os.path.exists(FILTER_FILE):
        save_json(FILTER_FILE, {
            "only_text": False,
            "only_image": False,
            "only_video": False,
            "only_link": False
        })
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"words": []})

def split_buttons(buttons, cols=2):
    return [buttons[i:i+cols] for i in range(0, len(buttons), cols)]

# /start
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "🤖 **Bot is active! Choose an action:**",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
            [Button.inline("📅 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("🪰 Filters", b"filters"), Button.inline("📝 Edit Word", b"edit_word")],
            [Button.inline("🚫 Blacklist Words", b"blacklist_words"), Button.inline("▶️ Toggle Blacklist", b"toggle_blacklist")],
            [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
        ]
    )

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.answer("Not authorized.")
        return

    data = event.data.decode()

    if data == "settings":
        s = load_json(SETTINGS_FILE)
        f = load_json(FORWARD_STATUS_FILE)
        w = load_json(REPLACE_FILE)
        b = load_json(BLACKLIST_FILE)
        text = "\U0001f4e6 **Settings**\n\n"
        text += f"🔄 Forwarding: {'✅ ON' if f.get('forwarding') else '❌ OFF'}\n"
        text += f"🚫 Blacklist: {'✅ ENABLED' if f.get('blacklist_enabled', True) else '❌ DISABLED'}\n"
        text += f"\n📥 Sources:\n" + "\n".join(s.get("source_channels", [])) or "None"
        text += f"\n\n📤 Targets:\n" + "\n".join(s.get("target_channels", [])) or "None"
        text += f"\n\n📝 Replacements:\n" + "\n".join([f"`{k}` → `{v}`" for k, v in w.get("words", {}).items()]) or "None"
        text += f"\n\n🚫 Blacklist Words:\n" + ", ".join(b.get("words", [])) or "None"
        await event.edit(text, parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "links": {}})
        save_json(BLACKLIST_FILE, {"words": []})
        await event.edit("♻️ All settings have been reset.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "forward":
        status = load_json(FORWARD_STATUS_FILE)
        status["forwarding"] = True
        save_json(FORWARD_STATUS_FILE, status)
        await event.edit("▶️ Forwarding started.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "stop":
        status = load_json(FORWARD_STATUS_FILE)
        status["forwarding"] = False
        save_json(FORWARD_STATUS_FILE, status)
        await event.edit("⏹️ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "toggle_blacklist":
        status = load_json(FORWARD_STATUS_FILE)
        status["blacklist_enabled"] = not status.get("blacklist_enabled", True)
        save_json(FORWARD_STATUS_FILE, status)
        await event.edit("✅ Blacklist toggled.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "filters":
        filters = load_json(FILTER_FILE)
        await event.edit(
            "🧰 **Toggle Filters:**",
            buttons=[
                [Button.inline(f"📝 Text: {'✅' if filters.get('only_text') else '❌'}", b"toggle_text"),
                 Button.inline(f"🖼 Image: {'✅' if filters.get('only_image') else '❌'}", b"toggle_image")],
                [Button.inline(f"🎥 Video: {'✅' if filters.get('only_video') else '❌'}", b"toggle_video"),
                 Button.inline(f"🔗 Link: {'✅' if filters.get('only_link') else '❌'}", b"toggle_link")],
                [Button.inline("🔙 Back", b"back_to_main")]
            ]
        )

    elif data.startswith("toggle_"):
        filters = load_json(FILTER_FILE)
        key = "only_" + data.split("_")[1]
        filters[key] = not filters.get(key, False)
        save_json(FILTER_FILE, filters)
        await handle_buttons(await event.edit("Updating..."))

    elif data == "edit_word":
        bot._last_action[uid] = "editword"
        await event.respond("✍️ Send replacements in `old → new` format, one per line")

    elif data == "blacklist_words":
        bot._last_action[uid] = "blacklist"
        await event.respond("✍️ Send blacklist words (comma-separated). To remove, resend without word.")

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send @username or channel ID or link for `{data}`")

    elif data == "back_to_main":
        await start(event)

@bot.on(events.NewMessage)
async def handle_input(event):
    uid = event.sender_id
    if not is_admin(uid):
        return

    if uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    text = event.text.strip()
    settings = load_json(SETTINGS_FILE)

    if action == "editword":
        replaces = {"words": {}, "links": {}}
        for line in text.split("\n"):
            if "→" in line:
                old, new = map(str.strip, line.split("→"))
                replaces["words"][old] = new
        save_json(REPLACE_FILE, replaces)
        await event.reply("✅ Replacements updated.")

    elif action == "blacklist":
        words = [w.strip() for w in text.split(",") if w.strip()]
        save_json(BLACKLIST_FILE, {"words": words})
        await event.reply(f"✅ Blacklist updated: {', '.join(words)}")

    elif action in ["add_source", "remove_source", "add_target", "remove_target"]:
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

# Start
init_files()
print("✅ Admin Bot Started.")
bot.run_until_disconnected()
