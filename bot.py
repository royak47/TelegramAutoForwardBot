import json
import os
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import GetFullChannelRequest

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
    if value.startswith("https://t.me/+") or value.startswith("t.me/+"):
        return value.split("+")[-1]  # Extract invite code only
    elif value.startswith("https://t.me/"):
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
            "only_link": False
        })
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"words": [], "enabled": True})

async def join_private_link(invite_code):
    try:
        result = await bot(ImportChatInviteRequest(invite_code))
        full = await bot(GetFullChannelRequest(result.chats[0]))
        return full.full_chat.id
    except Exception as e:
        print(f"❌ Failed to join private link: {e}")
        return None

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    settings = load_json(SETTINGS_FILE)
    s_list = "\n".join(settings.get("source_channels", [])).replace("-100", "`) `-100")
    t_list = "\n".join(settings.get("target_channels", [])).replace("-100", "`) `-100")

    await event.respond(
        f"🤖 **Bot is active! Choose an action:**\n\n**Source Channels:**\n`s {s_list}`\n\n**Target Channels:**\n`t {t_list}`",
        parse_mode="markdown",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
            [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("🔙 Back", b"back_to_main")]
        ]
    )

@bot.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if not is_admin(uid):
        return

    if uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    text = event.raw_text.strip()
    settings = load_json(SETTINGS_FILE)

    key = "source_channels" if "source" in action else "target_channels"
    norm = normalize(text)

    if re.match(r"^[A-Za-z0-9_-]{16,}", norm):
        new_id = await join_private_link(norm)
        if not new_id:
            await event.reply("❌ Failed to join or fetch private channel ID.")
            return
        norm = str(new_id)

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
print("✅ Admin Bot running...")
bot.run_until_disconnected()

