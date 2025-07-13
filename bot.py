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
            "replace_enabled": True,
            "remove_mentions_enabled": False
        })
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"enabled": False, "words": []})


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
            [Button.inline("📅 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📄 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("🩰 Filters", b"filters"), Button.inline("📝 Edit Word", b"edit_word")],
            [Button.inline("❌ Blacklist Words", b"blacklist_words"), Button.inline("✉️ Mention Filter", b"edit_mention")],
            [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
        ]
    )


@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid):
        if hasattr(event, "answer"):
            return await event.answer("Not allowed.")
        return

    data = event.data.decode()
    settings = load_json(SETTINGS_FILE)
    filters = load_json(FILTER_FILE)
    blacklist = load_json(BLACKLIST_FILE)
    replaces = load_json(REPLACE_FILE)

    if data == "settings":
        text = "📆 **Settings**\n\n"
        text += f"🔄 Forwarding: {'✅ ON' if load_json(FORWARD_STATUS_FILE).get('forwarding') else '❌ OFF'}\n"
        text += f"📅 Sources:\n" + "\n".join(settings.get("source_channels", []) or ["None"])
        text += f"\n\n📄 Targets:\n" + "\n".join(settings.get("target_channels", []) or ["None"])
        text += f"\n\n📝 Replacements:\n" + "\n".join([f"`{k}` → `{v}`" for k, v in replaces.get("words", {}).items()]) or "None"
        await event.edit(text, parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "mentions": {}})
        save_json(BLACKLIST_FILE, {"enabled": False, "words": []})
        await event.edit("♻️ All settings reset.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding started.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        await event.edit(
            "🩰 **Toggle Filters:**",
            buttons=[
                [Button.inline(f"📝 Text: {'✅' if filters.get('only_text') else '❌'}", b"toggle_text"),
                 Button.inline(f"🖼 Image: {'✅' if filters.get('only_image') else '❌'}", b"toggle_image")],
                [Button.inline(f"🎥 Video: {'✅' if filters.get('only_video') else '❌'}", b"toggle_video"),
                 Button.inline(f"🔗 Link: {'✅' if filters.get('only_link') else '❌'}", b"toggle_link")],
                [Button.inline(f"🔄 Replace: {'✅' if filters.get('replace_enabled') else '❌'}", b"toggle_replace"),
                 Button.inline(f"✉️ @Filter: {'✅' if filters.get('remove_mentions_enabled') else '❌'}", b"toggle_mentions")],
                [Button.inline(f"❌ Blacklist: {'✅' if blacklist.get('enabled') else '❌'}", b"toggle_blacklist")],
                [Button.inline("🔙 Back", b"back")]
            ]
        )

    elif data.startswith("toggle_"):
        key = data.split("_", 1)[1]
        if key == "blacklist":
            blacklist["enabled"] = not blacklist.get("enabled")
            save_json(BLACKLIST_FILE, blacklist)
        else:
            toggle_key = "only_" + key if key in ["text", "image", "video", "link"] else ("replace_enabled" if key == "replace" else "remove_mentions_enabled")
            filters[toggle_key] = not filters.get(toggle_key, False)
            save_json(FILTER_FILE, filters)
        await handle_buttons(event)

    elif data == "edit_word":
        bot._last_action[uid] = "editword"
        await event.respond("✍️ Send replacements like: `old | new`", parse_mode="markdown")

    elif data == "edit_mention":
        bot._last_action[uid] = "mentionword"
        await event.respond("✍️ Send @mention|@your_username to replace", parse_mode="markdown")

    elif data == "blacklist_words":
        bot._last_action[uid] = "blacklist"
        await event.respond("✍️ Send blacklist words comma-separated.")

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send @username or channel ID for `{data}`")

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
    settings = load_json(SETTINGS_FILE)
    replaces = load_json(REPLACE_FILE)

    if action == "editword":
        if "|" not in text:
            return await event.reply("❗ Format: old | new")
        old, new = map(str.strip, text.split("|", 1))
        replaces.setdefault("words", {})[old] = new
        save_json(REPLACE_FILE, replaces)
        await event.reply(f"✅ `{old}` → `{new}` added.", parse_mode="markdown")

    elif action == "mentionword":
        if "|" not in text:
            return await event.reply("❗ Format: @mention | @your_username")
        old, new = map(str.strip, text.split("|", 1))
        replaces.setdefault("mentions", {})[old] = new
        save_json(REPLACE_FILE, replaces)
        await event.reply(f"✅ `{old}` → `{new}` mention updated.", parse_mode="markdown")

    elif action == "blacklist":
        words = [w.strip() for w in text.split(",") if w.strip()]
        save_json(BLACKLIST_FILE, {"enabled": True, "words": words})
        await event.reply(f"✅ Blacklist: {', '.join(words)}")

    elif action in ["add_source", "remove_source", "add_target", "remove_target"]:
        key = "source_channels" if "source" in action else "target_channels"
        value = normalize(text)
        if "add" in action:
            if value not in settings[key]:
                settings[key].append(value)
                await event.reply(f"✅ Added `{value}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Already exists.")
        else:
            if value in settings[key]:
                settings[key].remove(value)
                await event.reply(f"❌ Removed `{value}`", parse_mode="markdown")
            else:
                await event.reply("⚠️ Not found.")
        save_json(SETTINGS_FILE, settings)


init_files()
print("✅ Admin Bot running...")
bot.run_until_disconnected()
