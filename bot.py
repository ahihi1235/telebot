import logging
import os
import requests
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- WEB SERVER ĐỂ RENDER KHÔNG NGỦ ---
web_app = Flask(__name__)
@web_app.route('/')
def health(): return "Bot is Alive", 200
def run_web(): 
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CẤU HÌNH ---
TOKEN = os.environ.get("TOKEN")
ADMIN_IDS = [1400175163]
API_URL = "https://saleavn.top/api.php" # Link đến file PHP của bạn
SECRET_KEY = "MINH_LA_ADMIN_123"
LIMIT = 2
REQUIRED_CHATS = ["@Nss247", "@sansaleshopee_lazada"]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- HÀM GỌI API ---
def call_api(action, params=None, json_data=None):
    p = params or {}
    p['key'] = SECRET_KEY
    p['action'] = action
    try:
        if json_data:
            return requests.post(API_URL, params=p, json=json_data, timeout=10).json()
        return requests.get(API_URL, params=p, timeout=10).json()
    except Exception as e:
        logging.error(f"API Error: {e}")
        return None

# --- XỬ LÝ LỖI (FIX ERROR HANDLER) ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

# --- LOGIC BOT ---
async def is_member(user_id, context):
    for chat in REQUIRED_CHATS:
        try:
            m = await context.bot.get_chat_member(chat, user_id)
            if m.status in ['member', 'administrator', 'creator']: return True
        except: continue
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update.effective_user.id, context):
        await update.message.reply_text("🚫 Bạn chưa tham gia kênh @Nss247 để nhận mã.")
        return
    
    cats = call_api('get_categories')
    if not cats:
        await update.message.reply_text("Kho mã hiện đang trống.")
        return

    keyboard = [[KeyboardButton(c['category'])] for c in cats]
    await update.message.reply_text("Chọn loại mã:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cat = update.message.text.strip()
    
    res = call_api('claim_link', {'user_id': user_id, 'category': cat, 'limit': LIMIT})
    if not res:
        await update.message.reply_text("Lỗi kết nối máy chủ.")
        return

    if res.get('status') == 'success':
        await update.message.reply_text(f"🎁 Link {cat}:\n{res['url']}")
    elif res.get('status') == 'limit_reached':
        await update.message.reply_text(f"🚫 Bạn đã hết lượt nhận {cat}.")
    else:
        await update.message.reply_text("Mã này đã hết.")

async def add_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        lines = update.message.text.split('\n')
        cat = lines[0].split()[1]
        urls = [l.strip() for l in lines[1:] if l.strip()]
        call_api('add_links', json_data={'category': cat, 'urls': urls})
        await update.message.reply_text(f"✅ Đã thêm {len(urls)} link cho {cat}.")
    except:
        await update.message.reply_text("Sai cú pháp: /add <tên_mã>\nLink 1\nLink 2")

def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    # Đăng ký xử lý lỗi
    app.add_error_handler(error_handler)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_links))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    
    app.run_polling()

if __name__ == '__main__': main()
