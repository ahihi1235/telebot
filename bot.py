import logging
import os
import requests
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# --- WEB SERVER (Cho Render) ---
web_app = Flask(__name__)
@web_app.route('/')
def health(): return "Bot is Alive", 200

def run_web(): 
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CẤU HÌNH ---
TOKEN = os.environ.get("TOKEN")
ADMIN_IDS = [1400175163]  # ID của bạn
API_URL = "https://salevn.top/api.php" 
SECRET_KEY = "MINH_LA_ADMIN_123"
LIMIT = 2
REQUIRED_CHATS = ["@Nss247", "@sansaleshopee_lazada"]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# --- HÀM BỔ TRỢ ---
# --- HÀM BỔ TRỢ ---
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

async def is_member(user_id, context: ContextTypes.DEFAULT_TYPE):
    """Kiểm tra người dùng đã Join Group/Channel chưa"""
    for chat_id in REQUIRED_CHATS:
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            logging.error(f"Lỗi kiểm tra thành viên tại {chat_id}: {e}")
            # Nếu bot chưa là Admin kênh, mặc định coi như chưa join để tránh lỗi logic
            return False
    return True

# --- ADMIN COMMANDS ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    res = call_api('status')
    if not res: 
        await update.message.reply_text("❌ Lỗi kết nối máy chủ API.")
        return
    
    msg = "📊 **THỐNG KÊ KHO MÃ**\n\n"
    for item in res.get('links', []):
        msg += f"🔸 {item['category']}: Còn {item['available']} - Đã phát {item['used']}\n"
    msg += f"\n👥 Tổng người dùng: {res.get('total_users', 0)}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def add_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        lines = update.message.text.split('\n')
        first_line = lines[0].split()
        if len(first_line) < 2: raise Exception()
        
        cat = first_line[1]
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
    user = update.effective_user
    try:
        # 1. Kiểm tra tham gia kênh
        if not await is_member(user.id, context):
            channels_str = "\n".join([f"👉 {c}" for c in REQUIRED_CHATS])
            await update.message.reply_text(
                f"🚫 **Bạn chưa tham gia kênh yêu cầu!**\n\nVui lòng tham gia các kênh sau để sử dụng bot:\n{channels_str}\n\nSau khi tham gia, hãy bấm lại /start",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 2. Lấy danh sách mã từ API
        cats = call_api('get_categories')
        
        if not cats or not isinstance(cats, list) or len(cats) == 0:
            await update.message.reply_text("🔄 Hiện tại kho mã đang tạm hết. Vui lòng quay lại sau!")
            return

        # 3. Xây dựng giao diện nút bấm
        instruction_lines = ""
        keyboard = []
        for c in cats:
            cat_name = str(c.get('category', ''))
            if cat_name:
                instruction_lines += f"- **{cat_name}** \n"
                keyboard.append([KeyboardButton(cat_name)])

        message = (
            "👋 gửi tin theo cú pháp bên dưới để lấy mã\n\n"
            f"{instruction_lines}\n"
            f"💡 Giới hạn: {LIMIT} code mỗi loại"
        )
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logging.error(f"Lỗi lệnh /start: {e}")
        await update.message.reply_text("⚠️ Có lỗi kỹ thuật, vui lòng thử lại sau.")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cat = update.message.text.strip()
    
    # Lấy thông tin người dùng để lưu log
    username = f"@{user.username}" if user.username else "N/A"
    full_name = user.full_name
    
    # Gửi yêu cầu lấy mã kèm thông tin người dùng lên API
    res = call_api('claim_link', {
        'user_id': user.id, 
        'username': username, 
        'full_name': full_name,
        'category': cat, 
        'limit': LIMIT
    })
    
    if not res:
        await update.message.reply_text("❌ Lỗi kết nối máy chủ.")
        return

    status = res.get('status')
    if status == 'success':
        await update.message.reply_text(f"🎁 **Link {cat} của bạn:**\n{res['url']}", parse_mode=ParseMode.MARKDOWN)
        logging.info(f"PHÁT MÃ: {username} lấy {cat}")
    elif status == 'limit_reached':
        await update.message.reply_text(f"🚫 Bạn đã nhận tối đa {LIMIT} lần cho loại mã này.")
    else:
        await update.message.reply_text("❌ Mã này đã hết hoặc không tồn tại.")

def main():
    # Chạy Web Server song song
    threading.Thread(target=run_web, daemon=True).start()
    
    # Khởi tạo Bot
    app = Application.builder().token(TOKEN).build()
    
    # --- CHỈ PHẢN HỒI TRONG CHAT RIÊNG (PRIVATE CHAT) ---
    private_filter = filters.ChatType.PRIVATE

    # Đăng ký lệnh Admin (Chỉ cho phép nhắn riêng)
    app.add_handler(CommandHandler("add", add_links, filters=private_filter))
    app.add_handler(CommandHandler("status", status, filters=private_filter))
    app.add_handler(CommandHandler("reset_users", reset_handler, filters=private_filter))
    app.add_handler(CommandHandler("resetall", reset_handler, filters=private_filter))
    
    # Lệnh User (Chỉ cho phép nhắn riêng)
    app.add_handler(CommandHandler("start", start, filters=private_filter))
    
    # MessageHandler: Chỉ xử lý tin nhắn TEXT, KHÔNG PHẢI COMMAND và PHẢI LÀ CHAT RIÊNG
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & private_filter, handle_msg))
    
    print("Bot is running in Private mode...")
    app.run_polling()

if __name__ == '__main__':
    main()
