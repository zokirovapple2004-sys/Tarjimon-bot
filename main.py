import logging
import os
import sqlite3
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from deep_translator import GoogleTranslator

# --- 1. SOZLAMALAR ---
# Yangi tokeningiz:
BOT_TOKEN = "8387200840:AAFMVfEWUhzB_C-25qjzajpQyRm5aF091hA"

# Sizning Admin ID raqamingiz:
ADMIN_ID = 8431876566

# --- 2. FLASK (RENDER UCHUN) ---
app = Flask('')

@app.route('/')
def home():
    return "Tarjimon Bot Ishlamoqda! (Alive)"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- 3. BAZA (SQLITE) ---
def init_db():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, name):
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if c.fetchone() is None:
        c.execute('INSERT INTO users VALUES (?, ?)', (user_id, name))
        conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users')
    return [row[0] for row in c.fetchall()]

def count_users():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    return c.fetchone()[0]

# --- 4. MENYULAR VA TILLAR ---
TILLAR = {
    "🇺🇿 O'zbek": "uz", "🇬🇧 English": "en", "🇷🇺 Русский": "ru",
    "🇰🇷 Korean": "ko", "🇸🇦 Arabic": "ar", "🇹🇷 Turkish": "tr",
    "🇯🇵 Japanese": "ja", "🇨🇳 Chinese": "zh-CN", "🇫🇷 French": "fr",
    "🇩🇪 German": "de", "🇮🇳 Hindi": "hi"
}

def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🌍 Tarjimon (Tilni tanlash)")],
        [KeyboardButton("📞 Admin / Taklif"), KeyboardButton("ℹ️ Biz haqimizda")],
        [KeyboardButton("⚙️ Sozlamalar")]
    ], resize_keyboard=True)

def lang_menu():
    keys = list(TILLAR.keys())
    buttons = [keys[i:i + 2] for i in range(0, len(keys), 2)]
    buttons.append(["🔙 Bosh menyu"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- 5. ASOSIY FUNKSIYALAR ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.first_name) # Bazaga yozamiz
    
    # Default sozlamalar
    if 'mode' not in context.user_data:
        context.user_data['mode'] = 'translate'
        context.user_data['lang'] = 'en'
        context.user_data['lang_name'] = "🇬🇧 English"

    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        "Men **Universal Tarjimon Botman**.\n"
        "Matn yozsangiz, uni avtomatik tarjima qilaman.\n\n"
        "Hozirgi til: **🇬🇧 English** (o'zgartirish uchun menyudan foydalaning).",
        reply_markup=main_menu()
    )

# --- ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        count = count_users()
        await update.message.reply_text(
            f"👑 **ADMIN PANEL**\n\n"
            f"👥 Jami foydalanuvchilar: {count} ta\n\n"
            f"📢 Reklama yuborish uchun: `/send Xabar` deb yozing.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⛔️ Bu bo'lim faqat admin uchun.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    msg = update.message.text[6:]
    if not msg:
        await update.message.reply_text("Xabar matni yo'q! M: /send Salom")
        return

    users = get_all_users()
    sent = 0
    await update.message.reply_text(f"🚀 Xabar {len(users)} kishiga yuborilmoqda...")
    
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=msg)
            sent += 1
        except:
            pass 
            
    await update.message.reply_text(f"✅ Xabar {sent} kishiga yetib bordi.")

# --- XABARLARNI QABUL QILISH ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_mode = context.user_data.get('mode', 'translate')

    # 1. MENYU BOSHQARUVI
    if text == "🌍 Tarjimon (Tilni tanlash)":
        await update.message.reply_text("Qaysi tilga tarjima qilay?", reply_markup=lang_menu())
        return

    elif text == "🔙 Bosh menyu":
        context.user_data['mode'] = 'translate'
        await update.message.reply_text("Asosiy menyuga qaytdik.", reply_markup=main_menu())
        return

    elif text == "📞 Admin / Taklif":
        context.user_data['mode'] = 'feedback'
        await update.message.reply_text(
            "✍️ **Adminga xabar yozing:**\n\n"
            "Taklif, shikoyat yoki fikringizni yozib qoldiring. Men yetkazaman.", 
            reply_markup=ReplyKeyboardMarkup([["🔙 Bosh menyu"]], resize_keyboard=True)
        )
        return

    elif text == "ℹ️ Biz haqimizda":
        await update.message.reply_text(
            "🤖 **Bot haqida**\n\n"
            "Bu bot 10 dan ortiq tillarni tushunadi va tarjima qiladi.\n"
            "Bot Python dasturlash tilida, Google Translate bazasida ishlaydi.",
            reply_markup=main_menu()
        )
        return

    elif text == "⚙️ Sozlamalar":
        til = context.user_data.get('lang_name', "🇬🇧 English")
        await update.message.reply_text(f"Hozirgi tarjima tili: **{til}**\nO'zgartirish uchun 'Tarjimon' tugmasini bosing.", reply_markup=main_menu())
        return

    # 2. TILNI O'ZGARTIRISH
    if text in TILLAR:
        context.user_data['lang'] = TILLAR[text]
        context.user_data['lang_name'] = text
        context.user_data['mode'] = 'translate'
        await update.message.reply_text(f"✅ Tayyor! Endi matnlarni **{text}**ga tarjima qilaman.", reply_markup=main_menu())
        return

    # 3. TARJIMA YOKI TAKLIF YUBORISH LOGIKASI
    if user_mode == 'feedback':
        # Adminga xabar yuborish
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
        await update.message.reply_text("✅ Xabaringiz adminga yuborildi! Javobni kuting.", reply_markup=main_menu())
        context.user_data['mode'] = 'translate' 
    
    else: # Translate mode
        target = context.user_data.get('lang', 'en')
        lang_nomi = context.user_data.get('lang_name', '🇬🇧 English')
        try:
            tarjima = GoogleTranslator(source='auto', target=target).translate(text)
            await update.message.reply_text(
                f"🌍 **{lang_nomi}:**\n`{tarjima}`",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text("Uzr, tarjima qilib bo'lmadi. Qayta urinib ko'ring.")

# --- ISHGA TUSHIRISH ---
if __name__ == '__main__':
    init_db()
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('admin', admin_panel))
    app.add_handler(CommandHandler('send', broadcast))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Yangi token bilan bot ishga tushdi!")
    app.run_polling()
