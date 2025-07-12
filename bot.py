import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REPLACE_FILE = "replacements.json"
FORWARD_STATUS_FILE = "forward_status.json"
BLOCKLIST_FILE = "blocklist.json"

bot = TelegramClient('admin_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def is_admin(user_id):
    with open(ADMIN_FILE, "r") as f:
        admins = json.load(f)
    return user_id in admins

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def init_files():
    if not os.path.exists(FORWARD_STATUS_FILE):
        save_json(FORWARD_STATUS_FILE, {
            "forwarding": True,
            "edit_sync": True,
            "delete_sync": True,
            "sticker_replace": False
        })
    if not os.path.exists(BLOCKLIST_FILE):
        save_json(BLOCKLIST_FILE, [])

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if not is_admin(event.sender_id): return
    await event.reply("✅ Bot is running!")

@bot.on(events.NewMessage(pattern="/forward"))
async def forward(event):
    if not is_admin(event.sender_id): return
    status = load_json(FORWARD_STATUS_FILE)
    status["forwarding"] = True
    save_json(FORWARD_STATUS_FILE, status)
    await event.reply("▶️ Forwarding started.")

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    if not is_admin(event.sender_id): return
    status = load_json(FORWARD_STATUS_FILE)
    status["forwarding"] = False
    save_json(FORWARD_STATUS_FILE, status)
    await event.reply("⏹️ Forwarding stopped.")

@bot.on(events.NewMessage(pattern="/settings"))
async def settings(event):
    if not is_admin(event.sender_id): return
    s = load_json(SETTINGS_FILE)
    f = load_json(FORWARD_STATUS_FILE)
    status = f"✅ ON" if f.get("forwarding") else "❌ OFF"
    text = f"📦 **Settings**\n\n"
    text += f"🔄 Forwarding: {status}\n"
    text += f"📥 Sources: {', '.join(map(str, s.get('source_channels', []))) or 'None'}\n"
    text += f"📤 Targets: {', '.join(map(str, s.get('target_channels', []))) or 'None'}"
    await event.reply(text)

@bot.on(events.NewMessage(pattern="/reset"))
async def reset(event):
    if not is_admin(event.sender_id): return
    save_json(SETTINGS_FILE, {"source_channels": [], "target_channels": []})
    save_json(REPLACE_FILE, {"words": {}, "links": {}})
    await event.reply("♻️ All settings have been reset.")

@bot.on(events.NewMessage(pattern="/setsource"))
async def set_source(event):
    if not is_admin(event.sender_id): return
    try:
        cid = int(event.message.text.split(" ")[1])
        settings = load_json(SETTINGS_FILE)
        if cid not in settings["source_channels"]:
            settings["source_channels"].append(cid)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"✅ Source channel added: {cid}")
        else:
            await event.reply("⚠️ Source already exists.")
    except:
        await event.reply("❗ Usage: /setsource CHANNEL_ID")

@bot.on(events.NewMessage(pattern="/removesource"))
async def remove_source(event):
    if not is_admin(event.sender_id): return
    try:
        cid = int(event.message.text.split(" ")[1])
        settings = load_json(SETTINGS_FILE)
        if cid in settings["source_channels"]:
            settings["source_channels"].remove(cid)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"❌ Source removed: {cid}")
        else:
            await event.reply("⚠️ Source not found.")
    except:
        await event.reply("❗ Usage: /removesource CHANNEL_ID")

@bot.on(events.NewMessage(pattern="/settarget"))
async def set_target(event):
    if not is_admin(event.sender_id): return
    try:
        cid = int(event.message.text.split(" ")[1])
        settings = load_json(SETTINGS_FILE)
        if cid not in settings["target_channels"]:
            settings["target_channels"].append(cid)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"✅ Target channel added: {cid}")
        else:
            await event.reply("⚠️ Target already exists.")
    except:
        await event.reply("❗ Usage: /settarget CHANNEL_ID")

@bot.on(events.NewMessage(pattern="/removetarget"))
async def remove_target(event):
    if not is_admin(event.sender_id): return
    try:
        cid = int(event.message.text.split(" ")[1])
        settings = load_json(SETTINGS_FILE)
        if cid in settings["target_channels"]:
            settings["target_channels"].remove(cid)
            save_json(SETTINGS_FILE, settings)
            await event.reply(f"❌ Target removed: {cid}")
        else:
            await event.reply("⚠️ Target not found.")
    except:
        await event.reply("❗ Usage: /removetarget CHANNEL_ID")

@bot.on(events.NewMessage(pattern="/addword"))
async def add_word(event):
    if not is_admin(event.sender_id): return
    try:
        old, new = event.message.text.split(" ", 2)[1:]
        data = load_json(REPLACE_FILE)
        data["words"][old] = new
        save_json(REPLACE_FILE, data)
        await event.reply(f"✅ Word replace rule added:\n{old} → {new}")
    except:
        await event.reply("❗ Usage: /addword old new")

@bot.on(events.NewMessage(pattern="/addlink"))
async def add_link(event):
    if not is_admin(event.sender_id): return
    try:
        old, new = event.message.text.split(" ", 2)[1:]
        data = load_json(REPLACE_FILE)
        data["links"][old] = new
        save_json(REPLACE_FILE, data)
        await event.reply(f"✅ Link replace rule added:\n{old} → {new}")
    except:
        await event.reply("❗ Usage: /addlink oldlink newlink")

@bot.on(events.NewMessage(pattern="/block"))
async def block_post(event):
    if not is_admin(event.sender_id): return
    try:
        text = event.message.text.split(" ", 1)[1]
        blocklist = load_json(BLOCKLIST_FILE)
        if text not in blocklist:
            blocklist.append(text)
            save_json(BLOCKLIST_FILE, blocklist)
            await event.reply(f"⛔ Blocked message: {text}")
        else:
            await event.reply("⚠️ Already blocked.")
    except:
        await event.reply("❗ Usage: /block text-to-block")

@bot.on(events.NewMessage(pattern="/(edit_sync|delete_sync|sticker_replace) ?(on|off)?"))
async def toggle(event):
    if not is_admin(event.sender_id): return
    args = event.message.text.split()
    forward_status = load_json(FORWARD_STATUS_FILE)
    if len(args) == 1:
        msg = "\n🔧 Toggles:\n"
        for key in ["edit_sync", "delete_sync", "sticker_replace"]:
            val = forward_status.get(key, False)
            msg += f"{key}: {'✅ ON' if val else '❌ OFF'}\n"
        await event.reply(msg)
    else:
        key = args[0].lstrip("/")
        val = args[1].lower()
        forward_status[key] = True if val == "on" else False
        save_json(FORWARD_STATUS_FILE, forward_status)
        await event.reply(f"🔄 {key} set to {val.upper()} ✅")

@bot.on(events.NewMessage(pattern="/viewreplacements"))
async def view_replacements(event):
    if not is_admin(event.sender_id): return
    data = load_json(REPLACE_FILE)
    msg = "📘 Current Replacements:\n"
    msg += "\nWords:\n" + "\n".join([f"{k} → {v}" for k, v in data.get("words", {}).items()])
    msg += "\n\nLinks:\n" + "\n".join([f"{k} → {v}" for k, v in data.get("links", {}).items()])
    await event.reply(msg)

@bot.on(events.NewMessage(pattern="/removeword"))
async def remove_word(event):
    if not is_admin(event.sender_id): return
    try:
        word = event.message.text.split(" ", 1)[1]
        data = load_json(REPLACE_FILE)
        if word in data["words"]:
            del data["words"][word]
            save_json(REPLACE_FILE, data)
            await event.reply(f"🗑️ Word removed: {word}")
        else:
            await event.reply("⚠️ Word not found.")
    except:
        await event.reply("❗ Usage: /removeword word")

@bot.on(events.NewMessage(pattern="/removelink"))
async def remove_link(event):
    if not is_admin(event.sender_id): return
    try:
        link = event.message.text.split(" ", 1)[1]
        data = load_json(REPLACE_FILE)
        if link in data["links"]:
            del data["links"][link]
            save_json(REPLACE_FILE, data)
            await event.reply(f"🗑️ Link removed: {link}")
        else:
            await event.reply("⚠️ Link not found.")
    except:
        await event.reply("❗ Usage: /removelink link")

init_files()
print("🤖 Admin bot started.")
bot.run_until_disconnected()
