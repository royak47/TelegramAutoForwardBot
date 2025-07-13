import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot._last_action = {}

ADMIN_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"
FORWARD_STATUS_FILE = "forward_status.json"
FILTER_FILE = "filters.json"
BLACKLIST_FILE = "blacklist.json"

def is_admin(uid):
    try:
        with open(ADMIN_FILE) as f:
            return uid in json.load(f)
    except:
        return False

def save_json(file, data): json.dump(data, open(file, "w"), indent=2)
def load_json(file): return json.load(open(file)) if os.path.exists(file) else {}

def normalize(value):
    value = value.strip()
    if value.startswith("https://t.me/"): return "@" + value.split("/")[-1]
    if value.startswith("t.me/"): return "@" + value.split("/")[-1]
    return value

def init_files():
    if not os.path.exists(FORWARD_STATUS_FILE): save_json(FORWARD_STATUS_FILE, {"forwarding": True})
    if not os.path.exists(SETTINGS_FILE): save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE): save_json(REPLACE_FILE, {"words": {}, "links": {}, "replace_mentions": ""})
    if not os.path.exists(FILTER_FILE):
        save_json(FILTER_FILE, {
            "only_text": False, "only_image": False, "only_video": False,
            "only_link": False, "blacklist_enabled": True
        })
    if not os.path.exists(BLACKLIST_FILE): save_json(BLACKLIST_FILE, {"words": []})

def split_buttons(buttons, cols=2): return [buttons[i:i+cols] for i in range(0, len(buttons), cols)]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id): return
    await event.respond("🤖 **Bot Menu:**", buttons=[
        [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
        [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
        [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
        [Button.inline("🧰 Filters", b"filters"), Button.inline("📝 Edit Word", b"edit_word")],
        [Button.inline("🚫 Blacklist", b"blacklist"), Button.inline("🔄 Mentions Replace", b"replace_mentions")],
        [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
    ])
    await event.delete()

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid): return await event.answer("Not authorized.")

    data = event.data.decode()
    settings, filters, replace = load_json(SETTINGS_FILE), load_json(FILTER_FILE), load_json(REPLACE_FILE)

    if data == "settings":
        fwd_status = load_json(FORWARD_STATUS_FILE).get("forwarding", False)
        text = f"📦 **Settings**\n\n🔄 Forwarding: {'✅ ON' if fwd_status else '❌ OFF'}"
        text += f"\n📥 Sources:\n" + "\n".join(settings["source_channels"]) or "None"
        text += f"\n\n📤 Targets:\n" + "\n".join(settings["target_channels"]) or "None"
        text += f"\n\n📝 Word Replacements:\n" + "\n".join([f"`{k}` → `{v}`" for k, v in replace["words"].items()]) or "None"
        await event.edit(text, parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "replace_mentions": ""})
        await event.edit("♻️ Settings reset!", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding **started**", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹️ Forwarding **stopped**", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "filters":
        await event.edit("🧰 **Toggle Filters**", buttons=[
            [Button.inline(f"📝 Text: {'✅' if filters['only_text'] else '❌'}", b"toggle_text"),
             Button.inline(f"🖼 Image: {'✅' if filters['only_image'] else '❌'}", b"toggle_image")],
            [Button.inline(f"🎥 Video: {'✅' if filters['only_video'] else '❌'}", b"toggle_video"),
             Button.inline(f"🔗 Link: {'✅' if filters['only_link'] else '❌'}", b"toggle_link")],
            [Button.inline(f"🚫 Blacklist: {'✅' if filters['blacklist_enabled'] else '❌'}", b"toggle_blacklist")],
            [Button.inline("🔙 Back", b"back_to_main")]
        ])

    elif data.startswith("toggle_"):
        key = data.split("_", 1)[1]
        filters[f"only_{key}" if key != "blacklist" else "blacklist_enabled"] = not filters.get(f"only_{key}" if key != "blacklist" else "blacklist_enabled", False)
        save_json(FILTER_FILE, filters)
        await handle_buttons(await event.edit("Updating..."))

    elif data == "edit_word":
        words = load_json(REPLACE_FILE)["words"]
        if not words: return await event.respond("❗ No words found.")
        btns = [Button.inline(f"{k}→{v}", f"editw_{k}".encode()) for k, v in words.items()]
        await event.edit("📝 Choose word to edit:", buttons=split_buttons(btns + [Button.inline("🔙 Back", b"back_to_main")], 2))

    elif data.startswith("editw_"):
        old_word = data.split("_", 1)[1]
        bot._last_action[uid] = f"editword:{old_word}"
        await event.respond(f"✍️ Send new word to replace `{old_word}`")

    elif data == "replace_mentions":
        bot._last_action[uid] = "replace_mentions"
        await event.respond("✍️ Send your bot ID to replace all `@mentions` (e.g., `@iamak_roy`)")

    elif data == "blacklist":
        bot._last_action[uid] = "blacklist"
        await event.respond("✍️ Send comma-separated blacklist words (e.g., `spam, scam, join`)")

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send username or ID to `{data}`")

    elif data == "back_to_main":
        await start(event)

@bot.on(events.NewMessage)
async def handle_input(event):
    uid = event.sender_id
    if not is_admin(uid) or uid not in bot._last_action: return

    action = bot._last_action.pop(uid)
    text = event.text.strip()
    settings = load_json(SETTINGS_FILE)

    if action.startswith("editword:"):
        old = action.split(":", 1)[1]
        data = load_json(REPLACE_FILE)
        if old in data["words"]:
            data["words"][old] = text
            save_json(REPLACE_FILE, data)
            await event.respond(f"✅ Updated `{old}` → `{text}`", parse_mode="markdown")

    elif action == "replace_mentions":
        data = load_json(REPLACE_FILE)
        data["replace_mentions"] = text
        save_json(REPLACE_FILE, data)
        await event.respond(f"✅ All `@something` will now become `{text}`")

    elif action == "blacklist":
        words = [w.strip() for w in text.split(",") if w.strip()]
        save_json(BLACKLIST_FILE, {"words": words})
        await event.respond(f"✅ Blacklist set:\n`{', '.join(words)}`", parse_mode="markdown")

    elif action in ["add_source", "remove_source", "add_target", "remove_target"]:
        key = "source_channels" if "source" in action else "target_channels"
        norm = normalize(text)
        if "add" in action:
            if norm not in settings[key]: settings[key].append(norm)
        else:
            if norm in settings[key]: settings[key].remove(norm)
        save_json(SETTINGS_FILE, settings)
        await event.respond(f"✅ Updated `{key}`:\n{norm}", parse_mode="markdown")

    await event.delete()

# Start
init_files()
print("✅ Admin Bot Ready.")
bot.run_until_disconnected()
