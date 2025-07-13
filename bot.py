import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

# Load .env variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# File paths
ADMIN_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"
FORWARD_STATUS_FILE = "forward_status.json"
FILTER_FILE = "filters.json"
BLACKLIST_FILE = "blacklist.json"

# Start bot
bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot._last_action = {}

# Utility functions
def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file):
    if not os.path.exists(file): return {}
    with open(file) as f: return json.load(f)

def is_admin(user_id):
    admins = load_json(ADMIN_FILE)
    return user_id in admins

def normalize(value):
    value = value.strip()
    if value.startswith("https://t.me/"):
        return value.split("/")[-1]
    if value.startswith("t.me/"):
        return value.split("/")[-1]
    return value

def init_files():
    if not os.path.exists(ADMIN_FILE): save_json(ADMIN_FILE, [])
    if not os.path.exists(SETTINGS_FILE): save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE): save_json(REPLACE_FILE, {"words": {}, "mentions": {}})
    if not os.path.exists(FORWARD_STATUS_FILE): save_json(FORWARD_STATUS_FILE, {"forwarding": True})
    if not os.path.exists(FILTER_FILE):
        save_json(FILTER_FILE, {
            "only_text": False, "only_image": False, "only_video": False,
            "only_link": False, "no_mentions": False
        })
    if not os.path.exists(BLACKLIST_FILE): save_json(BLACKLIST_FILE, {"enabled": False, "words": []})

# Display settings
def display_settings():
    s = load_json(SETTINGS_FILE)
    r = load_json(REPLACE_FILE)
    f = load_json(FORWARD_STATUS_FILE)
    bl = load_json(BLACKLIST_FILE)
    filters = load_json(FILTER_FILE)
    
    settings = f"""
📦 **Settings:**
🔄 Forwarding: {'✅' if f.get('forwarding') else '❌'}

📥 Sources: {len(s['source_channels'])} channel(s)
📤 Targets: {len(s['target_channels'])} channel(s)

📝 Word Replacements: {len(r['words'])}
🔁 Mention Replacements: {len(r['mentions'])}
🚫 Blacklist Enabled: {'✅' if bl.get('enabled') else '❌'} ({len(bl.get('words', []))} word(s))

🔧 Filters:
  - Text: {'✅' if filters.get('only_text') else '❌'}
  - Image: {'✅' if filters.get('only_image') else '❌'}
  - Video: {'✅' if filters.get('only_video') else '❌'}
  - Link: {'✅' if filters.get('only_link') else '❌'}
  - Remove Mentions (@): {'✅' if filters.get('no_mentions') else '❌'}
    """
    return settings

# Button setup
def main_menu():
    return [
        [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
        [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
        [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
        [Button.inline("📝 Edit Word", b"edit_word"), Button.inline("@ Mention Edit", b"mention_edit")],
        [Button.inline("🚫 Blacklist Toggle", b"toggle_blacklist"), Button.inline("✍️ Blacklist Words", b"blacklist_words")],
        [Button.inline("🧰 Filters", b"filters")],
        [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id): return
    await event.respond("🤖 **Bot is active! Choose an action:**", buttons=main_menu())

@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    uid = event.sender_id
    if not is_admin(uid): return
    data = event.data.decode()

    if data == "settings":
        await event.edit(display_settings(), parse_mode="markdown", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        save_json(REPLACE_FILE, {"words": {}, "mentions": {}})
        save_json(BLACKLIST_FILE, {"enabled": False, "words": []})
        await event.edit("✅ All settings reset!", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding started!", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹️ Forwarding stopped!", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "toggle_blacklist":
        bl = load_json(BLACKLIST_FILE)
        bl['enabled'] = not bl.get('enabled', False)
        save_json(BLACKLIST_FILE, bl)
        await event.edit(f"🚫 Blacklist {'enabled' if bl['enabled'] else 'disabled'}!", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        f = load_json(FILTER_FILE)
        await event.edit("🧰 Toggle filters:", buttons=[
            [Button.inline(f"Text: {'✅' if f['only_text'] else '❌'}", b"toggle_text"),
             Button.inline(f"Image: {'✅' if f['only_image'] else '❌'}", b"toggle_image")],
            [Button.inline(f"Video: {'✅' if f['only_video'] else '❌'}", b"toggle_video"),
             Button.inline(f"Link: {'✅' if f['only_link'] else '❌'}", b"toggle_link")],
            [Button.inline(f"@ Mentions: {'✅' if f['no_mentions'] else '❌'}", b"toggle_mentions")],
            [Button.inline("🔙 Back", b"back")]
        ])

    elif data.startswith("toggle_"):
        f = load_json(FILTER_FILE)
        key = data.split("toggle_")[1]
        f[f"only_{key}" if key != "mentions" else "no_mentions"] = not f.get(f"only_{key}" if key != "mentions" else "no_mentions", False)
        save_json(FILTER_FILE, f)
        await handle_buttons(event)

    elif data == "back":
        await event.edit("🤖 Back to menu:", buttons=main_menu())

# Run
init_files()
print("✅ Admin Bot running...")
bot.run_until_disconnected()

