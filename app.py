from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
import sqlite3
import os

# ================= CONFIG =================
TOKEN = 
"8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]
METHOD_COST = 7
INVITE_REWARD = 1

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    referred_by INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS channels (
    channel TEXT
)
""")

conn.commit()

# ================= HELPERS =================
def is_admin(uid):
    return uid in ADMINS

def get_points(uid):
    c.execute("SELECT points FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    return r[0] if r else 0

async def check_join(uid, bot):
    c.execute("SELECT channel FROM channels")
    for (ch,) in c.fetchall():
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        ref = int(args[0]) if args else None
        c.execute("INSERT INTO users(user_id, referred_by) VALUES (?,?)", (uid, ref))
        if ref:
            c.execute(
                "UPDATE users SET points = points + ? WHERE user_id=?",
                (INVITE_REWARD, ref)
            )
        conn.commit()

    await update.message.reply_text(
        f"👋 Welcome!\n\n"
        f"💰 Points: {get_points(uid)}\n"
        f"👥 Invite = +{INVITE_REWARD} Point\n"
        f"🧠 Method Cost = {METHOD_COST} Points\n\n"
        f"/account – My Account\n"
        f"/methods – Method List"
    )

# ================= ACCOUNT =================
async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    link = f"https://t.me/{context.bot.username}?start={uid}"

    await update.message.reply_text(
        f"👤 User ID: {uid}\n"
        f"💰 Points: {get_points(uid)}\n\n"
        f"🔗 Referral Link:\n{link}"
    )

# ================= METHODS =================
async def methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT id, title FROM methods")
    rows = c.fetchall()

    if not rows:
        await update.message.reply_text("❌ No methods available")
        return

    text = "📚 Method List:\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]}\n"

    text += "\nUse: /getmethod ID"
    await update.message.reply_text(text)

async def getmethod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not await check_join(uid, context.bot):
        await update.message.reply_text("❗ Please join all channels first")
        return

    if get_points(uid) < METHOD_COST:
        await update.message.reply_text("❌ Not enough points")
        return

    if not context.args:
        await update.message.reply_text("❗ Use: /getmethod ID")
        return

    mid = int(context.args[0])
    c.execute("SELECT content FROM methods WHERE id=?", (mid,))
    row = c.fetchone()

    if not row:
        await update.message.reply_text("❌ Method not found")
        return

    c.execute(
        "UPDATE users SET points = points - ? WHERE user_id=?",
        (METHOD_COST, uid)
    )
    conn.commit()

    await update.message.reply_text(f"✅ Method Unlocked:\n\n{row[0]}")

# ================= ADMIN =================
async def addmethod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    data = update.message.text.split("|", 2)
    if len(data) < 3:
        await update.message.reply_text("Use:\n/addmethod | Title | Content")
        return
    c.execute(
        "INSERT INTO methods(title, content) VALUES (?,?)",
        (data[1].strip(), data[2].strip())
    )
    conn.commit()
    await update.message.reply_text("✅ Method Added")

async def addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return
    c.execute("INSERT INTO channels VALUES (?)", (context.args[0],))
    conn.commit()
    await update.message.reply_text("✅ Channel Added")

async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    uid, pts = map(int, context.args)
    c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (pts, uid))
    conn.commit()
    await update.message.reply_text("✅ Points Added")

async def cutpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    uid, pts = map(int, context.args)
    c.execute("UPDATE users SET points = points - ? WHERE user_id=?", (pts, uid))
    conn.commit()
    await update.message.reply_text("✅ Points Cut")

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    msg = update.message.text.replace("/broadcast", "").strip()
    c.execute("SELECT user_id FROM users")
    for (u,) in c.fetchall():
        try:
            await context.bot.send_message(u, msg)
        except:
            pass
    await update.message.reply_text("✅ Broadcast Sent")

async def fwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    c.execute("SELECT user_id FROM users")
    for (u,) in c.fetchall():
        try:
            await context.bot.forward_message(
                chat_id=u,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except:
            pass

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("account", account))
app.add_handler(CommandHandler("methods", methods))
app.add_handler(CommandHandler("getmethod", getmethod))

app.add_handler(CommandHandler("addmethod", addmethod))
app.add_handler(CommandHandler("addchannel", addchannel))
app.add_handler(CommandHandler("addpoints", addpoints))
app.add_handler(CommandHandler("cutpoints", cutpoints))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("fwd", fwd))

app.run_polling()
