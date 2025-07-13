import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import ImportChatInviteRequest

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
    if value.startswith("https://t.me/+"):
        return value.split("+")[-1]  # return only the invite code
    elif value.startswith("https://t.me/"):
        return "@" + value.split("/")[-1]
    elif value.startswith("t.me/+"):
        return value.split("+")[-1]
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
            "block_mentions": False
        })
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"enabled": False, "words": []})


@bot.on(events.NewMessage(pattern="/test_forward"))
async def test_forward(event):
    if not is_admin(event.sender_id):
        return
    settings = load_json(SETTINGS_FILE)
    text = "Testing forward to all targets"
    for target in settings.get("target_channels", []):
        try:
            if target.startswith("@"):
                await bot.send_message(target, text)
            elif target.startswith("https://t.me/+") or len(target) == 22:
                invite = target.split("+")[-1]
                update = await bot(ImportChatInviteRequest(invite))
                await bot.send_message(update.chats[0].id, text)
            elif target.startswith("-100") or target.isdigit():
                await bot.send_message(int(target), text)
            else:
                await bot.send_message(target, text)
            print(f"✅ Sent to: {target}")
        except Exception as e:
            print(f"❌ Failed for {target}: {e}")
    await event.respond("✅ Test message sent to targets.")


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "🤖 Bot is Active! Use the panel below:",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
            [Button.inline("📥 Add Source", b"add_source"), Button.inline("❌ Remove Source", b"remove_source")],
            [Button.inline("📤 Add Target", b"add_target"), Button.inline("❌ Remove Target", b"remove_target")],
            [Button.inline("🧰 Filters", b"filters")],
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
        fl = load_json(FILTER_FILE)
        bl = load_json(BLACKLIST_FILE)
        text = "\n📦 **Settings**\n"
        text += f"\n🔄 Forwarding: {'✅ ON' if f.get('forwarding') else '❌ OFF'}"
        text += f"\n📥 Sources: {len(s.get('source_channels', []))}"
        text += f"\n📤 Targets: {len(s.get('target_channels', []))}"
        text += f"\n🚫 Blacklist Enabled: {'✅' if bl.get('enabled') else '❌'}"
        text += f"\n🔗 Filters: Text({fl.get('only_text')}), Image({fl.get('only_image')}), Video({fl.get('only_video')}), Link({fl.get('only_link')})"
        await event.edit(
            text,
            buttons=[[Button.inline("🔙 Back", b"back_to_main")]],
            parse_mode="markdown"
        )

    elif data == "reset":
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
        await event.edit("♻️ Settings reset.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding started.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹️ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back_to_main")]])

    elif data == "filters":
        filters = load_json(FILTER_FILE)
        await event.edit(
            "🧰 Toggle Filters:",
            buttons=[
                [Button.inline(f"Text: {'✅' if filters.get('only_text') else '❌'}", b"toggle_text"),
                 Button.inline(f"Image: {'✅' if filters.get('only_image') else '❌'}", b"toggle_image")],
                [Button.inline(f"Video: {'✅' if filters.get('only_video') else '❌'}", b"toggle_video"),
                 Button.inline(f"Link: {'✅' if filters.get('only_link') else '❌'}", b"toggle_link")],
                [Button.inline(f"@Mentions: {'✅' if filters.get('block_mentions') else '❌'}", b"toggle_mentions")],
                [Button.inline("🔙 Back", b"back_to_main")]
            ]
        )

    elif data.startswith("toggle_"):
        filters = load_json(FILTER_FILE)
        key = "only_" + data.split("_")[1] if not data.endswith("mentions") else "block_mentions"
        filters[key] = not filters.get(key, False)
        save_json(FILTER_FILE, filters)
        await handle_buttons(event)

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond(f"✍️ Send @username, channel ID, or invite link for `{data}`", parse_mode="markdown")

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

    if action in ["add_source", "remove_source", "add_target", "remove_target"]:
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
print("✅ Admin Bot running...")
bot.run_until_disconnected()

