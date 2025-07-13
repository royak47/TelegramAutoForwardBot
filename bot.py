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
    if not os.path.exists(ADMIN_FILE):
        save_json(ADMIN_FILE, [])
    if not os.path.exists(FORWARD_STATUS_FILE):
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE):
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "mentions": {}})
    if not os.path.exists(FILTER_FILE):
        save_json(FILTER_FILE, {
            "only_text": False,
            "only_image": False,
            "only_video": False,
            "only_link": False,
            "remove_mentions": False
        })
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"enabled": False, "words": []})

def get_status_symbol(value):
    return "✅" if value else "❌"

def split_buttons(buttons, cols=2):
    return [buttons[i:i+cols] for i in range(0, len(buttons), cols)]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "🤖 **Bot Control Panel:**",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
            [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("🧰 Filters", b"filters"), Button.inline("✍️ Edit Word", b"edit_word")],
            [Button.inline("🚫 Blacklist Words", b"blacklist_words"), Button.inline("✍️ Edit Mentions", b"edit_mentions")],
            [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
        ]
    )

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid):
        return

    data = event.data.decode()

    if data == "settings":
        s = load_json(SETTINGS_FILE)
        f = load_json(FORWARD_STATUS_FILE)
        w = load_json(REPLACE_FILE)
        b = load_json(BLACKLIST_FILE)
        filters = load_json(FILTER_FILE)
        text = "📦 **Settings**\n\n"
        text += f"🔄 Forwarding: {get_status_symbol(f.get('forwarding'))}\n"
        text += f"🚫 Blacklist: {get_status_symbol(b.get('enabled'))}\n"
        text += f"🚷 Mentions Remove: {get_status_symbol(filters.get('remove_mentions'))}\n"
        text += f"📝 Text: {get_status_symbol(filters.get('only_text'))} | 🖼 Img: {get_status_symbol(filters.get('only_image'))} | 🎥 Vid: {get_status_symbol(filters.get('only_video'))} | 🔗 Link: {get_status_symbol(filters.get('only_link'))}\n"
        text += f"\n📥 Sources: {len(s.get('source_channels', []))}"
        text += f"\n📤 Targets: {len(s.get('target_channels', []))}"
        text += f"\n🔄 Replacements: {len(w.get('words', {}))} | Mentions: {len(w.get('mentions', {}))}"
        text += f"\n🚫 Blacklist Words: {len(b.get('words', []))}"
        await event.edit(text, parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "mentions": {}})
        save_json(BLACKLIST_FILE, {"enabled": False, "words": []})
        save_json(FILTER_FILE, {
            "only_text": False, "only_image": False, "only_video": False, "only_link": False, "remove_mentions": False
        })
        await event.edit("♻️ All settings reset.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        f = load_json(FILTER_FILE)
        await event.edit(
            "🧰 **Toggle Filters:**",
            buttons=[
                [Button.inline(f"📝 Text: {get_status_symbol(f.get('only_text'))}", b"toggle_only_text"),
                 Button.inline(f"🖼 Image: {get_status_symbol(f.get('only_image'))}", b"toggle_only_image")],
                [Button.inline(f"🎥 Video: {get_status_symbol(f.get('only_video'))}", b"toggle_only_video"),
                 Button.inline(f"🔗 Link: {get_status_symbol(f.get('only_link'))}", b"toggle_only_link")],
                [Button.inline(f"🚷 Mentions: {get_status_symbol(f.get('remove_mentions'))}", b"toggle_remove_mentions")],
                [Button.inline("🔙 Back", b"back")]
            ]
        )

    elif data.startswith("toggle_"):
        key = data.replace("toggle_", "")
        f = load_json(FILTER_FILE)
        f[key] = not f.get(key, False)
        save_json(FILTER_FILE, f)
        await handle_buttons(await event.edit("Updating..."))

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding started.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "blacklist_words":
        bot._last_action[uid] = "blacklist"
        await event.respond("✍️ Send blacklist words (comma separated). Type `off` to disable blacklist.", parse_mode="markdown")

    elif data == "edit_word":
        bot._last_action[uid] = "editword"
        await event.respond("✍️ Send in format `old|new`, multiple allowed separated by new lines.", parse_mode="markdown")

    elif data == "edit_mentions":
        bot._last_action[uid] = "mentions"
        await event.respond("✍️ Send @mention|@your_name per line. Multiple supported.", parse_mode="markdown")

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send @username or channel ID or link for `{data}`", parse_mode="markdown")

    elif data == "back":
        await start(event)

@bot.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if not is_admin(uid):
        return

    if uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    text = event.text.strip()

    if action in ["add_source", "remove_source", "add_target", "remove_target"]:
        key = "source_channels" if "source" in action else "target_channels"
        s = load_json(SETTINGS_FILE)
        norm = normalize(text)
        if "add" in action:
            if norm not in s[key]:
                s[key].append(norm)
                await event.respond(f"✅ Added: `{norm}`", parse_mode="markdown")
            else:
                await event.respond("⚠️ Already exists.")
        else:
            if norm in s[key]:
                s[key].remove(norm)
                await event.respond(f"❌ Removed: `{norm}`", parse_mode="markdown")
            else:
                await event.respond("⚠️ Not found.")
        save_json(SETTINGS_FILE, s)

    elif action == "blacklist":
        bl = load_json(BLACKLIST_FILE)
        if text.lower() == "off":
            bl["enabled"] = False
        else:
            bl["enabled"] = True
            bl["words"] = [w.strip() for w in text.replace("\n", ",").split(",") if w.strip()]
        save_json(BLACKLIST_FILE, bl)
        await event.respond(f"✅ Blacklist updated.")

    elif action == "editword":
        r = load_json(REPLACE_FILE)
        lines = [l for l in text.strip().splitlines() if "|" in l]
        for line in lines:
            old, new = map(str.strip, line.split("|", 1))
            r["words"][old] = new
        save_json(REPLACE_FILE, r)
        await event.respond("✅ Word replacements updated.")

    elif action == "mentions":
        r = load_json(REPLACE_FILE)
        if "mentions" not in r:
            r["mentions"] = {}
        lines = [l for l in text.strip().splitlines() if "|" in l]
        for line in lines:
            old, new = map(str.strip, line.split("|", 1))
            r["mentions"][old] = new
        save_json(REPLACE_FILE, r)
        await event.respond("✅ Mention replacements updated.")

init_files()
print("✅ Admin Bot running...")
bot.run_until_disconnected()
