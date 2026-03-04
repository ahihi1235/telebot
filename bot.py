import logging
import os
import requests
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- WEB SERVER ---
web_app = Flask(__name__)
@web_app.route('/')
def health(): return "Bot is Alive", 200
def run_web(): 
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CẤU HÌNH ---
TOKEN = os.environ.get("TOKEN")
ADMIN_IDS = [1400175163]
API_URL = "https://salevn.top/api.php" 
SECRET_KEY = "MINH_LA_ADMIN_123"
LIMIT = 2
REQUIRED_CHATS = ["@Nss247", "@sansaleshopee_lazada"]

logging.basicConfig(level=logging.INFO)

def call_api(action, params=None, json_data=None):
    p = params or {}
    p['key'] = SECRET_KEY
    p['action'] = action
    try:
        if json_data:
            r = requests.post(API_URL, params=p, json=json_data, timeout=15)
        else:
            r = requests.get(API_URL, params=p, timeout=15)
        return r.json()
    except Exception as e:
        logging.error(f"API Error ({action}): {e}")
        return None

# --- ADMIN COMMANDS ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    res = call_api('status')
    if not res: 
        await update.message.reply_text("❌ Lỗi kết nối máy chủ API.")
        return
    
    msg = "📊 **THỐNG KÊ KHO MÃ**\n\n"
    for item in res['links']:
        msg += f"🔸 {item['category']}: Còn {item['available']} - Đã phát {item['used']}\n"
    msg += f"\n👥 Tổng người dùng: {res['total_users']}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        lines = update.message.text.split('\n')
        first_line = lines[0].split()
        if len(first_line) < 2: raise Exception()
        
        cat = first_line[1] # Ví dụ: 70/250
        urls = [l.strip() for l in lines[1:] if l.strip()]
        
        res = call_api('add_links', json_data={'category': cat, 'urls': urls})
        if res and res.get('status') == 'ok':
            await update.message.reply_text(f"✅ Đã thêm {res['added']} link cho {cat}.")
        else:
            await update.message.reply_text("❌ Lỗi: Host không phản hồi JSON đúng.")
    except:
        await update.message.reply_text("⚠️ Sai cú pháp! Hãy nhập:\n/add Tên_Mã\nLink1\nLink2")

async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    cmd = update.message.text
    action = 'reset_all' if 'all' in cmd else 'reset_users'
    res = call_api(action)
    if res and res.get('status') == 'ok':
        await update.message.reply_text(f"✅ Đã thực hiện: {action}")
    else:
        await update.message.reply_text("❌ Thất bại.")

# --- USER COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("❌ Lỗi kết nối máy chủ.")
        return

    if res.get('status') == 'success':
        await update.message.reply_text(f"🎁 Link {cat}:\n{res['url']}")
    elif res.get('status') == 'limit_reached':
        await update.message.reply_text(f"🚫 Bạn đã nhận tối đa {LIMIT} lần cho loại mã này.")
    else:
        await update.message.reply_text("Mã này đã hết hoặc không tồn tại.")

def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    # Đăng ký lệnh Admin
    app.add_handler(CommandHandler("add", add_links))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("reset_users", reset_handler))
    app.add_handler(CommandHandler("resetall", reset_handler))
    
    # Lệnh User
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__': main()
