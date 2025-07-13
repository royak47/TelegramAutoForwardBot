import json, os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = TelegramClient("admin_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot._last_action = {}

FILES = {
    "admins": "admins.json",
    "settings": "settings.json",
    "forward": "forward_status.json",
    "replacements": "replacements.json",
    "filters": "filters.json",
    "blacklist": "blacklist.json"
}

def load_json(file): return json.load(open(FILES[file])) if os.path.exists(FILES[file]) else {}
def save_json(file, data): json.dump(data, open(FILES[file], "w"), indent=2)
def is_admin(uid): return uid in load_json("admins")
def normalize(text): return "@" + text.split("/")[-1].lstrip("@") if "t.me" in text else text.strip()

def init():
    if not os.path.exists(FILES["admins"]): save_json("admins", [])
    if not os.path.exists(FILES["settings"]): save_json("settings", {"source_channels": [], "target_channels": []})
    if not os.path.exists(FILES["forward"]): save_json("forward", {"forwarding": True})
    if not os.path.exists(FILES["replacements"]): save_json("replacements", {"words": {}, "links": {}, "mentions": {}})
    if not os.path.exists(FILES["filters"]): save_json("filters", {
        "only_text": False, "only_image": False, "only_video": False, "only_link": False
    })
    if not os.path.exists(FILES["blacklist"]): save_json("blacklist", {"enabled": False, "words": []})

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id): return
    await event.delete()
    await event.respond("🤖 **Auto Forward Bot Control Panel**", buttons=[
        [Button.inline("⚙️ Settings", b"settings"), Button.inline("♻️ Reset", b"reset")],
        [Button.inline("📥 Add Source", b"add_source"), Button.inline("📤 Add Target", b"add_target")],
        [Button.inline("❌ Remove Source", b"remove_source"), Button.inline("❌ Remove Target", b"remove_target")],
        [Button.inline("📝 Word Replace", b"edit_word"), Button.inline("📛 Mentions", b"mention_replace")],
        [Button.inline("🚫 Blacklist", b"blacklist"), Button.inline("🧰 Filters", b"filters")],
        [Button.inline("▶️ Start", b"forward"), Button.inline("⏹ Stop", b"stop")]
    ])

@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    if not is_admin(uid): return await event.answer("Not allowed", alert=True)
    data = event.data.decode()

    if data == "settings":
        s = load_json("settings")
        f = load_json("forward")["forwarding"]
        bl = load_json("blacklist")
        await event.edit(f"⚙️ **Settings:**\n\n"
            f"🔄 Forwarding: {'✅ ON' if f else '❌ OFF'}\n"
            f"📥 Source(s):\n" + "\n".join(s["source_channels"]) + "\n\n" +
            f"📤 Target(s):\n" + "\n".join(s["target_channels"]) + "\n\n" +
            f"🚫 Blacklist: {'✅ Enabled' if bl['enabled'] else '❌ Disabled'}\n",
            buttons=[[Button.inline("🔙 Back", b"back")]]
        )

    elif data == "reset":
        save_json("settings", {"source_channels": [], "target_channels": []})
        save_json("replacements", {"words": {}, "links": {}, "mentions": {}})
        await event.edit("♻️ Config reset done.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "forward":
        save_json("forward", {"forwarding": True})
        await event.edit("▶️ Forwarding started.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "stop":
        save_json("forward", {"forwarding": False})
        await event.edit("⏹️ Forwarding stopped.", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data in ["add_source", "remove_source", "add_target", "remove_target"]:
        bot._last_action[uid] = data
        await event.respond("✍️ Send @username / ID / link now")

    elif data == "edit_word":
        bot._last_action[uid] = "edit_word"
        await event.respond("✍️ Send in format:\n`old|new`")

    elif data == "mention_replace":
        bot._last_action[uid] = "edit_mention"
        await event.respond("✍️ Send `@mention|@your_username`")

    elif data == "blacklist":
        bl = load_json("blacklist")
        await event.edit("🚫 **Blacklist Menu**", buttons=[
            [Button.inline("✍️ Edit Words", b"bl_edit"), Button.inline(f"🔄 Toggle: {'✅ ON' if bl['enabled'] else '❌ OFF'}", b"bl_toggle")],
            [Button.inline("🔙 Back", b"back")]
        ])

    elif data == "bl_edit":
        bot._last_action[uid] = "edit_blacklist"
        await event.respond("✍️ Send blacklist words (comma separated)")

    elif data == "bl_toggle":
        bl = load_json("blacklist")
        bl["enabled"] = not bl["enabled"]
        save_json("blacklist", bl)
        await event.edit(f"🔄 Blacklist {'Enabled ✅' if bl['enabled'] else 'Disabled ❌'}", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "filters":
        fl = load_json("filters")
        await event.edit("🧰 **Filter Toggles**", buttons=[
            [Button.inline(f"📝 Text: {'✅' if fl['only_text'] else '❌'}", b"toggle_text"),
             Button.inline(f"🖼 Image: {'✅' if fl['only_image'] else '❌'}", b"toggle_image")],
            [Button.inline(f"🎥 Video: {'✅' if fl['only_video'] else '❌'}", b"toggle_video"),
             Button.inline(f"🔗 Link: {'✅' if fl['only_link'] else '❌'}", b"toggle_link")],
            [Button.inline("🔙 Back", b"back")]
        ])

    elif data.startswith("toggle_"):
        key = "only_" + data.split("_")[1]
        fl = load_json("filters")
        fl[key] = not fl.get(key, False)
        save_json("filters", fl)
        await event.edit("✅ Filter Updated!", buttons=[[Button.inline("🔙 Back", b"back")]])

    elif data == "back":
        await start(event)

@bot.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if not is_admin(uid): return
    if uid not in bot._last_action: return
    action = bot._last_action.pop(uid)
    text = event.text.strip()
    s = load_json("settings")

    if action in ["add_source", "remove_source", "add_target", "remove_target"]:
        key = "source_channels" if "source" in action else "target_channels"
        norm = normalize(text)
        if "add" in action:
            if norm not in s[key]: s[key].append(norm)
        else:
            if norm in s[key]: s[key].remove(norm)
        save_json("settings", s)
        await event.reply(f"✅ Updated {key}: {norm}")

    elif action == "edit_word":
        old, new = map(str.strip, text.split("|"))
        r = load_json("replacements")
        r["words"][old] = new
        save_json("replacements", r)
        await event.reply(f"✅ `{old}` → `{new}`")

    elif action == "edit_mention":
        old, new = map(str.strip, text.split("|"))
        r = load_json("replacements")
        r["mentions"][old] = new
        save_json("replacements", r)
        await event.reply(f"✅ `{old}` → `{new}`")

    elif action == "edit_blacklist":
        bl_words = [w.strip() for w in text.split(",") if w.strip()]
        bl = load_json("blacklist")
        bl["words"] = bl_words
        save_json("blacklist", bl)
        await event.reply("✅ Blacklist updated.")

init()
print("✅ Admin bot running.")
bot.run_until_disconnected()
