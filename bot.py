# ✅ Full bot.py with all features & clean layout
# Works on Mobile/PC screen (cleaned + all toggles)

import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# File paths
ADMIN_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"
FORWARD_STATUS_FILE = "forward_status.json"
FILTER_FILE = "filters.json"
BLACKLIST_FILE = "blacklist.json"

bot._last_action = {}

# Init files
def init_files():
    def create(file, default):
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump(default, f, indent=2)

    create(ADMIN_FILE, [])
    create(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    create(REPLACE_FILE, {"words": {}, "mentions": {}})
    create(FORWARD_STATUS_FILE, {"forwarding": True, "blacklist_enabled": True})
    create(FILTER_FILE, {
        "only_text": False, "only_image": False,
        "only_video": False, "only_link": False,
        "block_mentions": False
    })
    create(BLACKLIST_FILE, {"words": []})

# Utils

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file):
    if not os.path.exists(file): return {}
    with open(file) as f:
        return json.load(f)

def is_admin(user_id):
    return user_id in load_json(ADMIN_FILE)

def normalize(val):
    if val.startswith("https://t.me/+"):
        return val.split("/+", 1)[-1]  # invite hash
    elif val.startswith("https://t.me/"):
        return "@" + val.split("/")[-1]
    elif val.startswith("t.me/"):
        return "@" + val.split("/")[-1]
    return val

def split_buttons(buttons, cols=2):
    return [buttons[i:i+cols] for i in range(0, len(buttons), cols)]

# Start message
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id): return
    await event.respond("🤖 **Bot is active! Choose an action:**", buttons=[
        [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
        [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
        [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
        [Button.inline("📝 Edit Word", b"edit_word"), Button.inline("✏️ Edit Mentions", b"edit_mentions")],
        [Button.inline("🚫 Blacklist Words", b"blacklist_words"), Button.inline("🧰 Filters", b"filters")],
        [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
    ])

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid): return await event.answer("Unauthorized")

    data = event.data.decode()
    s = load_json(SETTINGS_FILE)
    f = load_json(FORWARD_STATUS_FILE)
    r = load_json(REPLACE_FILE)
    b = load_json(BLACKLIST_FILE)
    fl = load_json(FILTER_FILE)

    if data == "settings":
        msg = f"""
📦 **Settings**

🔄 Forwarding: {'✅' if f['forwarding'] else '❌'}
🚫 Blacklist: {'✅' if f.get('blacklist_enabled') else '❌'}

📥 Sources ({len(s['source_channels'])}):\n" + "\n".join(s['source_channels']) + "\n"
        msg += f"\n📤 Targets ({len(s['target_channels'])}):\n" + "\n".join(s['target_channels']) + "\n"
        msg += f"\n✏️ Replacements: {len(r['words'])} | Mentions: {len(r['mentions'])}"
        msg += f"\n🚫 Blacklist: {', '.join(b['words']) or 'None'}"
        await event.edit(msg, buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "mentions": {}})
        await event.edit("♻️ Settings reset.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "forward":
        f['forwarding'] = True
        save_json(FORWARD_STATUS_FILE, f)
        await event.edit("▶️ Forwarding enabled.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "stop":
        f['forwarding'] = False
        save_json(FORWARD_STATUS_FILE, f)
        await event.edit("⏹️ Forwarding disabled.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        btns = [
            Button.inline(f"Text {'✅' if fl['only_text'] else '❌'}", b"toggle_text"),
            Button.inline(f"Image {'✅' if fl['only_image'] else '❌'}", b"toggle_image"),
            Button.inline(f"Video {'✅' if fl['only_video'] else '❌'}", b"toggle_video"),
            Button.inline(f"Link {'✅' if fl['only_link'] else '❌'}", b"toggle_link"),
            Button.inline(f"@Mentions {'✅' if fl['block_mentions'] else '❌'}", b"toggle_mentions"),
            Button.inline(f"Blacklist {'✅' if f['blacklist_enabled'] else '❌'}", b"toggle_blacklist")
        ]
        await event.edit("🧰 **Toggle Filters**", buttons=split_buttons(btns + [Button.inline("🔙 Back", b"back")], 2))

    elif data.startswith("toggle_"):
        key = data.split("_")[1]
        if key == "blacklist":
            f['blacklist_enabled'] = not f.get('blacklist_enabled', True)
            save_json(FORWARD_STATUS_FILE, f)
        else:
            fl['only_' + key if key != 'mentions' else 'block_mentions'] = not fl.get('only_' + key if key != 'mentions' else 'block_mentions', False)
            save_json(FILTER_FILE, fl)
        await handle_buttons(event)

    elif data in ["add_source", "remove_source", "add_target", "remove_target", "blacklist_words"]:
        bot._last_action[uid] = data
        await event.respond("✍️ Send input:", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data in ["edit_word", "edit_mentions"]:
        bot._last_action[uid] = data
        await event.respond("✍️ Send in format `from|to` (one per message)", parse_mode="markdown")

    elif data == "back":
        await start(event)

@bot.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if not is_admin(uid): return
    if uid not in bot._last_action: return

    action = bot._last_action.pop(uid)
    txt = event.text.strip()

    s = load_json(SETTINGS_FILE)
    r = load_json(REPLACE_FILE)
    b = load_json(BLACKLIST_FILE)

    def reply(msg): return event.reply(msg, parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back")]])

    if action.startswith("edit_"):
        if "|" not in txt: return await reply("❗ Format: `from|to`")
        old, new = map(str.strip, txt.split("|", 1))
        key = "mentions" if "mentions" in action else "words"
        r[key][old] = new
        save_json(REPLACE_FILE, r)
        return await reply(f"✅ Updated {key}: `{old}` → `{new}`")

    elif action == "blacklist_words":
        b["words"] = list(set(w.strip() for w in txt.split(",") if w.strip()))
        save_json(BLACKLIST_FILE, b)
        return await reply("✅ Blacklist updated.")

    elif action.startswith("add") or action.startswith("remove"):
        key = "source_channels" if "source" in action else "target_channels"
        val = normalize(txt)
        if "add" in action:
            if val not in s[key]: s[key].append(val)
            await reply(f"✅ Added: `{val}`")
        else:
            if val in s[key]: s[key].remove(val)
            await reply(f"❌ Removed: `{val}`")
        save_json(SETTINGS_FILE, s)

# Start bot
init_files()
print("✅ Admin Bot running...")
bot.run_until_disconnected()
