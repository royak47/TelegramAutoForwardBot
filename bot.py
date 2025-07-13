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

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot._last_action = {}

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
    if not os.path.exists(FILTER_FILE):
        save_json(FILTER_FILE, {
            "only_text": False,
            "only_image": False,
            "only_video": False,
            "only_link": False
        })

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
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("📊 Filters", b"filters"), Button.inline("🖍 Edit Word", b"edit_word")],
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
        text = "📦 **Settings**\n\n"
        text += f"🔄 Forwarding: {'✅ ON' if f.get('forwarding') else '❌ OFF'}\n"
        text += f"📅 Sources:\n" + "\n".join(s.get("source_channels", [])) or "None"
        text += f"\n\n📤 Targets:\n" + "\n".join(s.get("target_channels", [])) or "None"
        text += f"\n\n🖍 Word Replacements:\n" + "\n".join([f"`{k}` → `{v}`" for k, v in w.get("words", {}).items()]) or "None"
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

    elif data == "filters":
        filters = load_json(FILTER_FILE)
        await event.edit(
            "🧰 **Toggle Filters:**",
            buttons=[
                [Button.inline(f"🖍 Text: {'✅' if filters.get('only_text') else '❌'}", b"toggle_text"),
                 Button.inline(f"🖼 Image: {'✅' if filters.get('only_image') else '❌'}", b"toggle_image")],
                [Button.inline(f"🎥 Video: {'✅' if filters.get('only_video') else '❌'}", b"toggle_video"),
                 Button.inline(f"🔗 Link: {'✅' if filters.get('only_link') else '❌'}", b"toggle_link")],
                [Button.inline("⬅️ Back", b"back_to_main")]
            ]
        )

    elif data.startswith("toggle_"):
        filters = load_json(FILTER_FILE)
        key = "only_" + data.split("_")[1]
        filters[key] = not filters.get(key, False)
        save_json(FILTER_FILE, filters)
        await handle_buttons(await event.edit("Updating..."))

    elif data == "back_to_main":
        await start(event)

    elif data == "edit_word":
        words = load_json(REPLACE_FILE).get("words", {})
        if not words:
            await event.respond("❗ No words to edit.")
            return
        btns = [Button.inline(f"{k} → {v}", f"editw_{k}".encode()) for k, v in words.items()]
        await event.edit("📝 Choose word to edit:", buttons=split_buttons(btns, 2))

@bot.on(events.CallbackQuery)
async def handle_edit_word_buttons(event):
    if event.data.startswith(b"editw_"):
        old_word = event.data.decode().split("_", 1)[1]
        bot._last_action[event.sender_id] = f"editword:{old_word}"
        await event.respond(f"✍️ Send new word to replace `{old_word}`", parse_mode="markdown")

@bot.on(events.NewMessage)
async def handle_input(event):
    uid = event.sender_id
    if not is_admin(uid):
        return
    if uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    text = event.text.strip()

    if action.startswith("editword:"):
        old_word = action.split(":", 1)[1]
        replaces = load_json(REPLACE_FILE)
        if old_word in replaces["words"]:
            replaces["words"][old_word] = text
            save_json(REPLACE_FILE, replaces)
            await event.reply(f"✅ Updated replacement:\n`{old_word}` → `{text}`", parse_mode="markdown")
        else:
            await event.reply("⚠️ Original word not found.")

# Init
init_files()
print("✅ Admin Bot Started.")
bot.run_until_disconnected()
