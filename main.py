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

# --- 2. FLASK (RENDER UCHUN) ---
app = Flask('')  # <-- BU SAYT NOMI (app)

@app.route('/')
def home():
    return "Bot V3 Ishlamoqda!"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

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

def get_all_users_ids():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users')
    return [row[0] for row in c.fetchall()]

# --- 4. TILLAR VA MENYULAR ---
TILLAR = {
    "🇺🇿 O'zbek": "uz", "🇬🇧 English": "en", "🇷🇺 Русский": "ru",
    "🇰🇷 Korean": "ko", "🇸🇦 Arabic": "ar", "🇹🇷 Turkish": "tr",
    "🇯🇵 Japanese": "ja", "🇩🇪 German": "de"
}

def main_menu_keyboard(user_id):
    buttons = [
        [KeyboardButton("🔤 Tarjima qilish"), KeyboardButton("👤 Profilim")],
        [KeyboardButton("⚙️ Sozlamalar"), KeyboardButton("ℹ️ Info")],
        [KeyboardButton("📞 Aloqa")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def settings_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🌐 Tilni o'zgartirish")],
        [KeyboardButton("🔙 Bosh menyu")]
    ], resize_keyboard=True)

def lang_menu_keyboard():
    keys = list(TILLAR.keys())
    buttons = [keys[i:i + 2] for i in range(0, len(keys), 2)]
    buttons.append([KeyboardButton("🔙 Orqaga")])
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
        f"👋 Salom, <b>{user.first_name}</b>! Men tayyorman.",
        reply_markup=main_menu_keyboard(user.id),
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state', 'main')

    # Navigatsiya
    if text == "🔙 Bosh menyu":
        context.user_data['state'] = 'main'
        await update.message.reply_text("🏠 Bosh menyu.", reply_markup=main_menu_keyboard(user_id))
        return
    if text == "🔙 Orqaga":
        context.user_data['state'] = 'settings'
        await update.message.reply_text("⚙️ Sozlamalar:", reply_markup=settings_menu_keyboard())
        return

    # Menyular
    if text == "🔤 Tarjima qilish":
        target = context.user_data.get('lang_name', '🇬🇧 English')
        await update.message.reply_text(
            f"Matn yozing ({target} ga o'giraman):",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bosh menyu")]], resize_keyboard=True)
        )
        context.user_data['state'] = 'translating'
        return
    elif text == "⚙️ Sozlamalar":
        context.user_data['state'] = 'settings'
        await update.message.reply_text("⚙️ Sozlamalar bo'limi:", reply_markup=settings_menu_keyboard())
        return
    elif text == "👤 Profilim":
        lang = context.user_data.get('lang_name', '🇬🇧 English')
        await update.message.reply_text(f"👤 ID: `{user_id}`\n🌐 Til: {lang}", parse_mode="Markdown")
        return
    elif text == "📞 Aloqa":
        context.user_data['state'] = 'feedback'
        await update.message.reply_text("Xabaringizni yozing:")
        return
    elif text == "ℹ️ Info":
        await update.message.reply_text("Bot Version 3.0 (Audio Support)")
        return
    
    # Admin Panel
    if text == "👑 Admin Panel" and user_id == ADMIN_ID:
        await update.message.reply_text("Admin commands: /send <text>")
        return

    # MANTIQ
    if state == 'settings' and text == "🌐 Tilni o'zgartirish":
        await update.message.reply_text("Tilni tanlang:", reply_markup=lang_menu_keyboard())
        context.user_data['state'] = 'changing_lang'
        return

    if state == 'changing_lang' and text in TILLAR:
        context.user_data['target_lang'] = TILLAR[text]
        context.user_data['lang_name'] = text
        context.user_data['state'] = 'settings'
        await update.message.reply_text(f"✅ Til o'zgardi: {text}", reply_markup=settings_menu_keyboard())
        return

    # --- TARJIMA VA AUDIO ---
    if state == 'translating':
        target_code = context.user_data.get('target_lang', 'en')
        try:
            tarjima = GoogleTranslator(source='auto', target=target_code).translate(text)
            
            # Audio tugmasi
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔊 Ovozli eshitish", callback_data=f"tts_{target_code}")
            ]])
            
            context.user_data['last_translation'] = tarjima
            await update.message.reply_text(f"📝 <b>Tarjima:</b>\n\n{tarjima}", reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            await update.message.reply_text("Tarjimada xatolik.")
        return

    if state == 'feedback':
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        await update.message.reply_text("✅ Yuborildi!", reply_markup=main_menu_keyboard(user_id))
        context.user_data['state'] = 'main'
        return

# --- AUDIO CALLBACK ---
async def audio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🎧 Ovoz yuklanmoqda...")
    try:
        data = query.data.split('_')
        lang_code = data[1]
        text_to_speak = context.user_data.get('last_translation', 'Hello')
        
        tts = gTTS(text=text_to_speak, lang=lang_code, slow=False)
        filename = "audio.mp3"
        tts.save(filename)
        
        await context.bot.send_audio(
            chat_id=query.message.chat_id,
            audio=open(filename, 'rb'),
            title="Tarjima",
            performer="@telegram_wbot"
        )
        os.remove(filename)
    except:
        await query.message.reply_text("Bu tilda ovoz mavjud emas.")

# --- START (TUZATILGAN QISM) ---
if __name__ == '__main__':
    init_db()
    keep_alive()
    
    # DIQQAT: O'zgaruvchi nomini 'application' qildim (eski kodda 'app' edi)
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('send', lambda u,c: None))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(audio_callback))
    
    print("Bot V3 ishga tushdi!")
    application.run_polling()
        context.user_data['state'] = 'translating'
        return
    elif text == "⚙️ Sozlamalar":
        context.user_data['state'] = 'settings'
        await update.message.reply_text("⚙️ Sozlamalar bo'limi:", reply_markup=settings_menu_keyboard())
        return
    elif text == "👤 Profilim":
        lang = context.user_data.get('lang_name', '🇬🇧 English')
        await update.message.reply_text(f"👤 ID: `{user_id}`\n🌐 Til: {lang}", parse_mode="Markdown")
        return
    elif text == "📞 Aloqa":
        context.user_data['state'] = 'feedback'
        await update.message.reply_text("Xabaringizni yozing:")
        return

    # MANTIQ
    if state == 'settings' and text == "🌐 Tilni o'zgartirish":
        await update.message.reply_text("Tilni tanlang:", reply_markup=lang_menu_keyboard())
        context.user_data['state'] = 'changing_lang'
        return

    if state == 'changing_lang' and text in TILLAR:
        context.user_data['target_lang'] = TILLAR[text]
        context.user_data['lang_name'] = text
        context.user_data['state'] = 'settings'
        await update.message.reply_text(f"✅ Til o'zgardi: {text}", reply_markup=settings_menu_keyboard())
        return

    # --- TARJIMA VA AUDIO QISMI ---
    if state == 'translating':
        target_code = context.user_data.get('target_lang', 'en')
        try:
            # 1. Tarjima
            tarjima = GoogleTranslator(source='auto', target=target_code).translate(text)
            
            # 2. Audio tugmasi (Inline Button)
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔊 Ovozli eshitish", callback_data=f"tts_{target_code}")
            ]])
            
            # 3. Tarjimani saqlab turamiz (Audio uchun)
            context.user_data['last_translation'] = tarjima
            
            await update.message.reply_text(f"📝 <b>Tarjima:</b>\n\n{tarjima}", reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            await update.message.reply_text("Xatolik.")
        return

    if state == 'feedback':
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        await update.message.reply_text("✅ Yuborildi!", reply_markup=main_menu_keyboard(user_id))
        context.user_data['state'] = 'main'
        return

# --- AUDIO CALLBACK HANDLER ---
async def audio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🎧 Ovoz yuklanmoqda...")
    
    try:
        data = query.data.split('_') # tts, en
        lang_code = data[1]
        text_to_speak = context.user_data.get('last_translation', 'Hello')
        
        # Ovoz faylini yaratamiz
        tts = gTTS(text=text_to_speak, lang=lang_code, slow=False)
        filename = "audio.mp3"
        tts.save(filename)
        
        # Jo'natamiz
        await context.bot.send_audio(chat_id=query.message.chat_id, audio=open(filename, 'rb'), title="Tarjima ovozi", performer="@telegram_wbot")
        os.remove(filename) # O'chiramiz
        
    except Exception as e:
        await query.message.reply_text("Ovozli formatda xatolik (bu til qo'llab-quvvatlanmasligi mumkin).")

# --- START ---
if __name__ == '__main__':
    init_db()
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('send', lambda u,c: None)) # Admin send qoldirildi
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(audio_callback)) # Audio uchun
    
    print("Bot V3 (Audio) ishga tushdi!")
    app.run_polling()
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
