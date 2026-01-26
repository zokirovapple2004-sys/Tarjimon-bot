import logging
import os
import sqlite3
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from deep_translator import GoogleTranslator
from gtts import gTTS

# --- 1. SOZLAMALAR ---
BOT_TOKEN = "8387200840:AAFMVfEWUhzB_C-25qjzajpQyRm5aF091hA"
ADMIN_ID = 8431876566

# --- 2. FLASK ---
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot V4.1 (Statistika) Ishlamoqda!"

def run_http():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- 3. BAZA VA STATISTIKA ---
def init_db():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, lang TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, name):
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if c.fetchone() is None:
        c.execute('INSERT INTO users VALUES (?, ?, ?)', (user_id, name, 'en'))
        conn.commit()
    conn.close()

# 📊 YANGI FUNKSIYA: Odam sonini sanash
def get_count():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    soni = c.fetchone()[0]
    conn.close()
    return soni

def get_all_ids():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users')
    return [row[0] for row in c.fetchall()]

# --- 4. MENYULAR ---
TILLAR = {
    "🇺🇿 O'zbek": "uz", "🇬🇧 English": "en", "🇷🇺 Русский": "ru",
    "🇰🇷 Korean": "ko", "🇸🇦 Arabic": "ar", "🇹🇷 Turkish": "tr",
    "🇯🇵 Japanese": "ja", "🇩🇪 German": "de", "🇨🇳 Chinese": "zh-CN"
}

def main_menu_keyboard(user_id):
    buttons = [
        [KeyboardButton("🔤 Tarjima qilish"), KeyboardButton("👤 Profilim")],
        [KeyboardButton("📞 Aloqa"), KeyboardButton("ℹ️ Info")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def translate_menu_keyboard():
    keys = list(TILLAR.keys())
    buttons = [keys[i:i + 2] for i in range(0, len(keys), 2)]
    buttons.append([KeyboardButton("🔙 Bosh menyu")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- 5. ASOSIY KOD ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.first_name)
    
    if 'target_lang' not in context.user_data:
        context.user_data['target_lang'] = 'en'
        context.user_data['lang_name'] = "🇬🇧 English"
        context.user_data['state'] = 'main'

    await update.message.reply_text(
        f"👋 Salom, <b>{user.first_name}</b>!\n\nTarjima qilishni boshlash uchun pastdagi tugmani bosing:",
        reply_markup=main_menu_keyboard(user.id),
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state', 'main')

    # NAVIGATION
    if text == "🔙 Bosh menyu":
        context.user_data['state'] = 'main'
        await update.message.reply_text("🏠 Asosiy menyu.", reply_markup=main_menu_keyboard(user_id))
        return

    # MENYULAR
    if text == "🔤 Tarjima qilish":
        target = context.user_data.get('lang_name', '🇬🇧 English')
        context.user_data['state'] = 'translating'
        await update.message.reply_text(
            f"Hozirgi til: <b>{target}</b>\nMatn yozing yoki tilni o'zgartiring: 👇",
            reply_markup=translate_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    elif text == "👤 Profilim":
        lang = context.user_data.get('lang_name', '🇬🇧 English')
        await update.message.reply_text(f"👤 <b>Siz:</b> {update.effective_user.first_name}\n🌐 <b>Tanlangan til:</b> {lang}", parse_mode="HTML")
        return

    elif text == "📞 Aloqa":
        context.user_data['state'] = 'feedback'
        await update.message.reply_text("Admin uchun xabar yozing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bosh menyu")]], resize_keyboard=True))
        return

    elif text == "ℹ️ Info":
        await update.message.reply_text("Bot V4.1 - Statistika qo'shildi.")
        return

    # 🔥 ADMIN PANEL (STATISTIKA SHU YERDA) 🔥
    if text == "👑 Admin Panel" and user_id == ADMIN_ID:
        odam_soni = get_count() # Bazadan sanab keladi
        await update.message.reply_text(
            f"👑 <b>ADMIN PANEL</b>\n\n"
            f"👥 <b>Jami obunachilar:</b> {odam_soni} ta\n\n"
            f"📢 Reklama yuborish uchun: <code>/send Xabar matni</code>",
            parse_mode="HTML"
        )
        return

    # TARJIMA REJIMI
    if state == 'translating':
        if text in TILLAR:
            context.user_data['target_lang'] = TILLAR[text]
            context.user_data['lang_name'] = text
            await update.message.reply_text(f"✅ Til o'zgardi: <b>{text}</b>", parse_mode="HTML", reply_markup=translate_menu_keyboard())
            return
        
        target_code = context.user_data.get('target_lang', 'en')
        try:
            tarjima = GoogleTranslator(source='auto', target=target_code).translate(text)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔊 Ovozli eshitish", callback_data=f"tts_{target_code}")]])
            context.user_data['last_translation'] = tarjima
            await update.message.reply_text(f"📝 <b>Tarjima:</b>\n\n{tarjima}", reply_markup=keyboard, parse_mode="HTML")
        except:
            await update.message.reply_text("Xatolik.")
        return

    # ALOQA
    if state == 'feedback':
        if user_id != ADMIN_ID:
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
            await update.message.reply_text("✅ Yuborildi!", reply_markup=main_menu_keyboard(user_id))
            context.user_data['state'] = 'main'
        return

# REKLAMA YUBORISH (/send)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = update.message.text[6:]
    if not msg:
        await update.message.reply_text("Matn yo'q. M: /send Salom")
        return
    ids = get_all_ids()
    await update.message.reply_text(f"🚀 {len(ids)} kishiga ketmoqda...")
    for uid in ids:
        try: await context.bot.send_message(uid, msg)
        except: pass
    await update.message.reply_text("✅ Tugadi.")

# AUDIO
async def audio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        data = query.data.split('_')
        lang = data[1]
        text = context.user_data.get('last_translation', 'Hello')
        tts = gTTS(text=text, lang=lang, slow=False)
        filename = "audio.mp3"
        tts.save(filename)
        await context.bot.send_audio(query.message.chat_id, open(filename, 'rb'), title="Ovoz", performer="Bot")
        os.remove(filename)
    except: await query.message.reply_text("Ovoz yo'q.")

if __name__ == '__main__':
    init_db()
    keep_alive()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('send', broadcast))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(audio_callback))
    print("Bot V4.1 ishga tushdi!")
    application.run_polling()
