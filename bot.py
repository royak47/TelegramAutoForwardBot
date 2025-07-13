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
            "blacklist_enabled": True
        })
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"words": []})

def split_buttons(buttons, cols=2):
    return [buttons[i:i+cols] for i in range(0, len(buttons), cols)]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "🤖 **Bot is active! Choose an action:**",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
            [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("🧰 Filters", b"filters"), Button.inline("📝 Edit Word", b"edit_word")],
            [Button.inline("🔄 Mention Replace", b"edit_mention"), Button.inline("🚫 Blacklist Words", b"blacklist_words")],
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
        bl = load_json(BLACKLIST_FILE)
        ft = load_json(FILTER_FILE)
        text = "📦 **Settings**\n\n"
        text += f"🔄 Forwarding: {'✅ ON' if f.get('forwarding') else '❌ OFF'}\n"
        text += f"🚫 Blacklist: {'✅ ON' if ft.get('blacklist_enabled', True) else '❌ OFF'}\n"
        text += f"📥 Sources:\n" + ("\n".join(s.get("source_channels", [])) or "None")
        text += f"\n\n📤 Targets:\n" + ("\n".join(s.get("target_channels", [])) or "None")
        text += f"\n\n📝 Word Replacements:\n" + ("\n".join([f"`{k}` → `{v}`" for k, v in w.get("words", {}).items()]) or "None")
        text += f"\n\n🔄 Mentions Replace:\n" + ("\n".join([f"{k} → {v}" for k, v in w.get("mentions", {}).items()]) or "None")
        text += f"\n\n🚫 Blacklist Words:\n" + (", ".join(bl.get("words", [])) or "None")
        await event.edit(text, parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "mentions": {}})
        save_json(BLACKLIST_FILE, {"words": []})
        await event.edit("♻️ All settings have been reset.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding started.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹️ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "filters":
        filters = load_json(FILTER_FILE)
        await event.edit(
            "🧰 **Toggle Filters:**",
            buttons=[
                [Button.inline(f"📝 Text: {'✅' if filters.get('only_text') else '❌'}", b"toggle_text"),
                 Button.inline(f"🖼 Image: {'✅' if filters.get('only_image') else '❌'}", b"toggle_image")],
                [Button.inline(f"🎥 Video: {'✅' if filters.get('only_video') else '❌'}", b"toggle_video"),
                 Button.inline(f"🔗 Link: {'✅' if filters.get('only_link') else '❌'}", b"toggle_link")],
                [Button.inline(f"🚫 Blacklist: {'✅' if filters.get('blacklist_enabled', True) else '❌'}", b"toggle_blacklist")],
                [Button.inline("🔙 Back", b"back_to_main")]
            ]
        )

    elif data.startswith("toggle_"):
        filters = load_json(FILTER_FILE)
        key = data.replace("toggle_", "only_") if "blacklist" not in data else "blacklist_enabled"
        filters[key] = not filters.get(key, False)
        save_json(FILTER_FILE, filters)
        await handle_buttons(await event.edit("Updating..."))

    elif data == "edit_word":
        words = load_json(REPLACE_FILE).get("words", {})
        if not words:
            await event.respond("❗ No words to edit.")
            return
        btns = [Button.inline(f"{k} → {v}", f"editw_{k}".encode()) for k, v in words.items()]
        await event.edit("📝 Choose word to edit:", buttons=split_buttons(btns + [Button.inline("🔙 Back", b"back_to_main")], 2))

    elif data == "edit_mention":
        bot._last_action[uid] = "edit_mention"
        await event.respond("✍️ Send `@mention | @your_username` to replace mentions")

    elif data == "blacklist_words":
        bot._last_action[uid] = "blacklist"
        await event.respond("✍️ Send words (comma-separated) to blacklist")

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send @username or channel ID or link for `{data}`")

    elif data == "back_to_main":
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
    settings = load_json(SETTINGS_FILE)

    if action == "blacklist":
        bl = [w.strip() for w in text.split(",") if w.strip()]
        save_json(BLACKLIST_FILE, {"words": bl})
        await event.reply(f"✅ Blacklist updated: {', '.join(bl)}")

    elif action == "edit_mention":
        if "|" not in text:
            await event.reply("⚠️ Use format: @mention | @your_username")
            return
        old, new = map(str.strip, text.split("|"))
        r = load_json(REPLACE_FILE)
        if "mentions" not in r:
            r["mentions"] = {}
        r["mentions"][old] = new
        save_json(REPLACE_FILE, r)
        await event.reply(f"✅ Mention updated: {old} → {new}")

    elif action.startswith("editword:"):
        old_word = action.split(":", 1)[1]
        replaces = load_json(REPLACE_FILE)
        if old_word in replaces["words"]:
            replaces["words"][old_word] = text
            save_json(REPLACE_FILE, replaces)
            await event.reply(f"✅ Updated replacement:\n`{old_word}` → `{text}`", parse_mode="markdown")
        else:
            await event.reply("⚠️ Original word not found.")

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

init_files()
print("✅ Admin Bot Started.")
bot.run_until_disconnected()

