import logging
import os
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from deep_translator import GoogleTranslator

# --- 1. RENDER UCHUN "YURAK" (Botni o'chirmaslik uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "Tarjimon Bot Ishlamoqda! (Alive)"

def run_http():
    # Render avtomatik beradigan portni olamiz
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- 2. SOZLAMALAR ---
BOT_TOKEN = "8551118204:AAG3JXUEz1ETnlXYQM9DtKRp6WZU5SD7-Pk" # <-- O'Z TOKENINGIZNI TEKSHIRING

# Tillarning to'liq ro'yxati (Tugmalar uchun)
TILLAR = {
    "🇺🇿 O'zbek": "uz",
    "🇬🇧 English": "en",
    "🇷🇺 Русский": "ru",
    "🇰🇷 Korean": "ko",
    "🇸🇦 Arabic": "ar",
    "🇹🇷 Turkish": "tr",
    "🇯🇵 Japanese": "ja",
    "🇨🇳 Chinese": "zh-CN",
    "🇫🇷 French": "fr",
    "🇩🇪 German": "de",
    "🇪🇸 Spanish": "es",
    "🇮🇳 Hindi": "hi",
    "🇮🇹 Italian": "it",
    "🇹🇯 Tajik": "tg",
    "🇰🇿 Kazakh": "kk"
}

# --- 3. BOT FUNKSIYALARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Default til: Ingliz tili
    if 'lang' not in context.user_data:
        context.user_data['lang'] = 'en'
        context.user_data['lang_nomi'] = "🇬🇧 English"

    # Tugmalarni 3 qator qilib joylaymiz
    keys = list(TILLAR.keys())
    menu_tugmalari = [keys[i:i + 3] for i in range(0, len(keys), 3)]
    
    await update.message.reply_text(
        "👋 **Universal Tarjimon Botga xush kelibsiz!**\n\n"
        "Men siz yozgan har qanday matnni avtomatik aniqlab, siz tanlagan tilga o'girib beraman.\n\n"
        "👇 **Qaysi tilga tarjima qilay? Tanlang:**",
        reply_markup=ReplyKeyboardMarkup(menu_tugmalari, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def xabarni_ishlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user.first_name
    
    # 1. Agar foydalanuvchi TIL tanlasa
    if text in TILLAR:
        context.user_data['lang'] = TILLAR[text]
        context.user_data['lang_nomi'] = text
        await update.message.reply_text(f"✅ Tushunarli! Endi hamma narsani **{text}**ga tarjima qilaman.")
        return

    # 2. Tarjima jarayoni
    target_lang = context.user_data.get('lang', 'en') # Xotiradagi til
    lang_nomi = context.user_data.get('lang_nomi', '🇬🇧 English')

    try:
        # Google Translate orqali tarjima
        tarjima = GoogleTranslator(source='auto', target=target_lang).translate(text)
        
        javob = (
            f"🗣 {text}\n"
            f"⬇️ ⬇️ ⬇️\n"
            f"{lang_nomi}: `{tarjima}`"
        )
        await update.message.reply_text(javob, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text("Uzr, tarjima xizmatida xatolik bo'ldi. Birozdan so'ng urinib ko'ring.")

# --- 4. ISHGA TUSHIRISH ---
if __name__ == '__main__':
    keep_alive() # Flaskni yoqamiz (Render uxlamasligi uchun)
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), xabarni_ishlash))
    
    print("Tarjimon Bot Renderda ishlashga tayyor! 🚀")
    app.run_polling()
