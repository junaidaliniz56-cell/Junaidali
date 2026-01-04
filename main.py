import telebot, os, json
from telebot import types
from collections import defaultdict

BOT_TOKEN = "8099789813:AAE1wYXxmU_auul3Lnt-fko_7kVyWwSln6Y"
ADMINS = [7011937754] [8191178194]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DATA_FILE = "numbers.json"
CHANNEL_FILE = "channels.json"
STATE = {}

def load(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

NUMBERS = load(DATA_FILE, {})
CHANNELS = load(CHANNEL_FILE, [])

FLAGS = {
    "Nepal": "🇳🇵", "Nigeria": "🇳🇬", "Ethiopia": "🇪🇹",
    "Comoros": "🇰🇲", "Cambodia": "🇰🇭",
    "Afghanistan": "🇦🇫", "Egypt": "🇪🇬"
}

def is_admin(uid): return uid in ADMINS
def flag(c): return FLAGS.get(c, "🌍")

# ================= JOIN CHECK =================
def check_join(uid):
    for ch in CHANNELS:
        try:
            m = bot.get_chat_member(ch["id"], uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    if not check_join(m.chat.id):
        kb = types.InlineKeyboardMarkup()
        for ch in CHANNELS:
            kb.add(types.InlineKeyboardButton(f"Join {ch['name']}", url=ch["link"]))
        kb.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
        bot.send_message(m.chat.id, "❌ Join required channels", reply_markup=kb)
        return

    show_countries(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data=="verify")
def verify(c):
    if check_join(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ Verified")
        show_countries(c.from_user.id)
    else:
        bot.answer_callback_query(c.id, "❌ Join all channels", show_alert=True)

# ================= USER PANEL =================
def show_countries(cid):
    if not NUMBERS:
        bot.send_message(cid, "❌ No numbers available")
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    for c in NUMBERS:
        kb.add(types.InlineKeyboardButton(
            f"{flag(c)} {c} ({len(NUMBERS[c])})",
            callback_data=f"country|{c}"
        ))
    kb.add(types.InlineKeyboardButton("🔄 Change Country", callback_data="change"))
    bot.send_message(cid, "🌍 <b>Select Country</b>", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def pick_country(c):
    country = c.data.split("|")[1]
    num = NUMBERS[country].pop(0)
    save(DATA_FILE, NUMBERS)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Change Number", callback_data=f"country|{country}"))
    kb.add(types.InlineKeyboardButton("📢 OTP Group", url="https://t.me/OtpXGroup"))
    kb.add(types.InlineKeyboardButton("🌍 Change Country", callback_data="change"))

    bot.edit_message_text(
        f"{flag(country)} <b>Your Number ({country})</b>\n\n📞 <code>{num}</code>\n\n⏳ Waiting for OTP...",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data=="change")
def change_country(c):
    show_countries(c.from_user.id)

# ================= ADMIN PANEL =================
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.chat.id): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Numbers", "📋 Number List")
    kb.add("➕ Add Channel", "📢 Channels")
    kb.add("❌ Close")
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=kb)

# ================= ADD NUMBERS =================
@bot.message_handler(func=lambda m: m.text=="➕ Add Numbers")
def add_numbers(m):
    STATE[m.chat.id] = "country"
    bot.send_message(m.chat.id, "🌍 Send Country Name")

@bot.message_handler(func=lambda m: STATE.get(m.chat.id)=="country")
def get_country(m):
    STATE[m.chat.id] = {"country": m.text}
    bot.send_message(m.chat.id, "📄 Send number.txt file")

@bot.message_handler(content_types=["document"])
def file_recv(m):
    st = STATE.get(m.chat.id)
    if not st or "country" not in st: return

    c = st["country"]
    file = bot.download_file(bot.get_file(m.document.file_id).file_path)
    nums = file.decode().splitlines()

    NUMBERS.setdefault(c, []).extend(nums)
    save(DATA_FILE, NUMBERS)

    bot.send_message(m.chat.id, f"✅ {len(nums)} numbers added to {c}")
    STATE.pop(m.chat.id)

# ================= NUMBER DELETE =================
@bot.message_handler(func=lambda m: m.text=="📋 Number List")
def list_numbers(m):
    kb = types.InlineKeyboardMarkup()
    for c in NUMBERS:
        kb.add(types.InlineKeyboardButton(
            f"{flag(c)} {c} ({len(NUMBERS[c])}) ❌",
            callback_data=f"delnum|{c}"
        ))
    bot.send_message(m.chat.id, "📋 Tap to delete country", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delnum|"))
def del_num(c):
    ctry = c.data.split("|")[1]
    del NUMBERS[ctry]
    save(DATA_FILE, NUMBERS)
    bot.edit_message_text(f"✅ {ctry} deleted", c.message.chat.id, c.message.message_id)

# ================= CHANNEL MANAGEMENT =================
@bot.message_handler(func=lambda m: m.text=="➕ Add Channel")
def add_channel(m):
    STATE[m.chat.id] = {}
    bot.send_message(m.chat.id, "📢 Send Channel Name")

@bot.message_handler(func=lambda m: isinstance(STATE.get(m.chat.id), dict) and "name" not in STATE[m.chat.id])
def ch_name(m):
    STATE[m.chat.id]["name"] = m.text
    bot.send_message(m.chat.id, "🔗 Send Channel Link")

@bot.message_handler(func=lambda m: isinstance(STATE.get(m.chat.id), dict) and "name" in STATE[m.chat.id])
def ch_link(m):
    ch = STATE[m.chat.id]
    CHANNELS.append({
        "name": ch["name"],
        "link": m.text,
        "id": m.text.replace("https://t.me/", "@")
    })
    save(CHANNEL_FILE, CHANNELS)
    bot.send_message(m.chat.id, "✅ Channel added")
    STATE.pop(m.chat.id)

@bot.message_handler(func=lambda m: m.text=="📢 Channels")
def list_channels(m):
    kb = types.InlineKeyboardMarkup()
    for i,ch in enumerate(CHANNELS):
        kb.add(types.InlineKeyboardButton(
            f"{ch['name']} ❌",
            callback_data=f"delch|{i}"
        ))
    bot.send_message(m.chat.id, "📢 Channel List", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delch|"))
def del_ch(c):
    i = int(c.data.split("|")[1])
    CHANNELS.pop(i)
    save(CHANNEL_FILE, CHANNELS)
    bot.edit_message_text("✅ Channel deleted", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text=="❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=types.ReplyKeyboardRemove())

print("🤖 Bot Running")
bot.infinity_polling()
