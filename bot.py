import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import ImportChatInviteRequest

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
        return value  # keep full private link
    if value.startswith("https://t.me/"):
        return "@" + value.split("/")[-1]
    elif value.startswith("t.me/"):
        return "@" + value.split("/")[-1]
    return value


def init_files():
    if not os.path.exists(ADMIN_FILE):
        save_json(ADMIN_FILE, [])
    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    if not os.path.exists(REPLACE_FILE):
        save_json(REPLACE_FILE, {"words": {}, "links": {}, "mentions": {}})
    if not os.path.exists(FORWARD_STATUS_FILE):
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
    if not os.path.exists(FILTER_FILE):
        save_json(FILTER_FILE, {
            "only_text": False,
            "only_image": False,
            "only_video": False,
            "only_link": False,
            "no_mentions": False
        })
    if not os.path.exists(BLACKLIST_FILE):
        save_json(BLACKLIST_FILE, {"enabled": False, "words": []})


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if event.sender_id not in load_json(ADMIN_FILE):
        return
    await event.respond(
        "🤖 **Bot Control Panel:**",
        buttons=[
            [Button.inline("⚙️ Settings", b"settings"), Button.inline("📄 Filters", b"filters")],
            [Button.inline("📥 Add Source", b"add_source"), Button.inline("📤 Add Target", b"add_target")],
            [Button.inline("📝 Replacements", b"edit_words"), Button.inline("🚫 Blacklist", b"blacklist")],
            [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")],
        ]
    )


@bot.on(events.CallbackQuery)
async def handle_buttons(event):
    user_id = event.sender_id
    if user_id not in load_json(ADMIN_FILE):
        return await event.answer("Not allowed.")

    data = event.data.decode()

    if data == "settings":
        s = load_json(SETTINGS_FILE)
        f = load_json(FORWARD_STATUS_FILE)
        bl = load_json(BLACKLIST_FILE)
        txt = f"\n🔄 Forwarding: {'ON' if f.get('forwarding') else 'OFF'}"
        txt += f"\n\n📥 Sources:\n" + "\n".join(s.get("source_channels", []))
        txt += f"\n\n📤 Targets:\n" + "\n".join(s.get("target_channels", []))
        txt += f"\n\n🚫 Blacklist: {'ON' if bl.get('enabled') else 'OFF'} ({len(bl.get('words', []))} words)"
        await event.edit("⚙️ **Current Settings:**\n" + txt, buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        f = load_json(FILTER_FILE)
        await event.edit(
            "🧰 **Toggle Filters:**",
            buttons=[
                [Button.inline(f"Text: {'✅' if f['only_text'] else '❌'}", b"toggle_text"),
                 Button.inline(f"Image: {'✅' if f['only_image'] else '❌'}", b"toggle_image")],
                [Button.inline(f"Video: {'✅' if f['only_video'] else '❌'}", b"toggle_video"),
                 Button.inline(f"Links: {'✅' if f['only_link'] else '❌'}", b"toggle_link")],
                [Button.inline(f"No @Mentions: {'✅' if f['no_mentions'] else '❌'}", b"toggle_mentions")],
                [Button.inline("🔙 Back", b"back")]
            ]
        )

    elif data.startswith("toggle_"):
        key = data.replace("toggle_", "only_") if data != "toggle_mentions" else "no_mentions"
        f = load_json(FILTER_FILE)
        f[key] = not f.get(key, False)
        save_json(FILTER_FILE, f)
        await event.edit("✅ Filter updated.", buttons=[[Button.inline("🔙 Back", b"filters")]])

    elif data == "add_source":
        bot._last_action[user_id] = "add_source"
        await event.respond("✍️ Send source @username or invite link")

    elif data == "add_target":
        bot._last_action[user_id] = "add_target"
        await event.respond("✍️ Send target @username or invite link")

    elif data == "edit_words":
        bot._last_action[user_id] = "edit_word"
        await event.respond("✍️ Send word pair like `bad|good` or `@old|@new`", parse_mode="markdown")

    elif data == "blacklist":
        bot._last_action[user_id] = "blacklist"
        await event.respond("✍️ Send blacklist words separated by comma. First word can be `on` or `off` to toggle.")

    elif data == "forward":
        save_json(FORWARD_STATUS_FILE, {"forwarding": True})
        await event.edit("▶️ Forwarding started.")

    elif data == "stop":
        save_json(FORWARD_STATUS_FILE, {"forwarding": False})
        await event.edit("⏹️ Forwarding stopped.")

    elif data == "back":
        await start(event)


@bot.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if uid not in load_json(ADMIN_FILE):
        return

    if uid not in bot._last_action:
        return

    action = bot._last_action.pop(uid)
    txt = event.raw_text.strip()

    if action in ["add_source", "add_target"]:
        settings = load_json(SETTINGS_FILE)
        key = "source_channels" if "source" in action else "target_channels"
        norm = normalize(txt)
        if norm not in settings[key]:
            settings[key].append(norm)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"✅ Added: `{norm}`", parse_mode="markdown")
        else:
            await event.reply("⚠️ Already exists.")

    elif action == "edit_word":
        try:
            old, new = map(str.strip, txt.split("|"))
            r = load_json(REPLACE_FILE)
            if old.startswith("@"):
                r.setdefault("mentions", {})[old] = new
            else:
                r.setdefault("words", {})[old] = new
            save_json(REPLACE_FILE, r)
            await event.reply(f"✅ Replacement saved: `{old}` → `{new}`", parse_mode="markdown")
        except:
            await event.reply("❌ Format error. Use `old|new`.", parse_mode="markdown")

    elif action == "blacklist":
        bl = load_json(BLACKLIST_FILE)
        parts = [w.strip() for w in txt.split(",") if w.strip()]
        if parts and parts[0].lower() in ["on", "off"]:
            bl["enabled"] = parts[0].lower() == "on"
            bl["words"] = parts[1:]
        else:
            bl["words"] = parts
        save_json(BLACKLIST_FILE, bl)
        await event.reply(f"✅ Blacklist updated ({'ON' if bl.get('enabled') else 'OFF'}): {len(bl['words'])} words")


init_files()
print("✅ Admin Bot running...")
bot.run_until_disconnected()

