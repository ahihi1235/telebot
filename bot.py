import logging
import os
import requests
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- WEB SERVER (GIỮ BOT KHÔNG NGỦ) ---
web_app = Flask(__name__)
@web_app.route('/')
def health(): return "OK", 200
def run_web(): os.environ.get("PORT", 8080); web_app.run(host='0.0.0.0', port=8080)

# --- CẤU HÌNH ---
TOKEN = os.environ.get("TOKEN")
ADMIN_IDS = [1400175163]
API_URL = "https://saleavn.top/api.php" # Thay bằng link file của bạn
API_KEY = "MINH_LA_ADMIN_123"
LIMIT_PER_CATEGORY = 2
REQUIRED_CHATS = ["@Nss247", "@sansaleshopee_lazada"]

logging.basicConfig(level=logging.INFO)

def call_api(action, params=None, json_data=None):
    params = params or {}
    params['key'] = API_KEY
    params['action'] = action
    if json_data:
        return requests.post(API_URL, params=params, json=json_data).json()
    return requests.get(API_URL, params=params).json()

async def is_member(user_id, context):
    for chat in REQUIRED_CHATS:
        try:
            m = await context.bot.get_chat_member(chat, user_id)
            if m.status in ['member', 'administrator', 'creator']: return True
        except: continue
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update.effective_user.id, context):
        await update.message.reply_text("🚫 Bạn chưa đủ điều kiện.")
        return
    
    cats = call_api('get_categories')
    if not cats:
        await update.message.reply_text("Kho mã đang trống.")
        return

    keyboard = [[KeyboardButton(c['category'])] for c in cats]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Chọn loại mã muốn nhận:", reply_markup=markup)

async def handle_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cat = update.message.text.strip()
    
    res = call_api('claim_link', {'user_id': user_id, 'category': cat, 'limit': LIMIT_PER_CATEGORY})
    
    if res.get('status') == 'success':
        await update.message.reply_text(f"🎁 Link {cat} (Lần {res['count']}):\n{res['url']}")
    elif res.get('status') == 'limit_reached':
        await update.message.reply_text(f"🚫 Bạn đã hết lượt nhận mã {cat}.")
    else:
        await update.message.reply_text("Mã này đã hết hoặc không tồn tại.")

# --- ADMIN COMMANDS ---
async def add_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    lines = update.message.text.split('\n')
    cat = lines[0].split()[1]
    urls = [l.strip() for l in lines[1:] if l.strip()]
    call_api('add_links', {'category': cat}, json_data={'category': cat, 'urls': urls})
    await update.message.reply_text(f"✅ Đã thêm {len(urls)} link.")

def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_links))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_request))
    app.run_polling()

if __name__ == '__main__': main()
