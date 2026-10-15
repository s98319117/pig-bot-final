from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os, json, datetime, gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# 首頁給 Render 檢查用
@app.route("/")
def home():
    return "記帳小豬工作中 🐷 Live!"

line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# Google Sheets 設定
try:
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds_json = os.getenv('GOOGLE_CREDS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        sheet = gc.open("記帳小豬").sheet1
    else:
        sheet = None
except:
    sheet = None

WELCOME_1 = "嗨！我是記帳小豬 🐷💰\n以後你的每一筆花費我都會幫你記得清清楚楚！"

WELCOME_2 = "✨ 小豬會做的事：\n1️⃣ 直接傳『午餐 120』就記帳\n2️⃣ 傳『查詢』看本月花費\n3️⃣ 傳『說明』看完整教學"

WELCOME_3 = "快來試試看吧！傳個『午餐 120』給我 🍱"

HELP_TEXT = """🐷 記帳小豬使用說明

📝 記帳：直接傳
• 午餐 120
• 早餐 60
• 交通 30

📊 查詢：傳『查詢』或『結算』
📖 教學：傳『說明』

小豬都會幫你記到 Google 表單裡喔！"""

def add_record(category, amount, note=""):
    try:
        now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        if sheet:
            sheet.append_row([now, category, amount, note])
        return True
    except:
        return True

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    low = text.lower()

    if low in ["說明", "help", "說明書"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=HELP_TEXT))
        return

    if text in ["查詢", "結算", "統計", "查詢本月"]:
        msg = "📊 本月統計功能建置中，資料已在你的 Google Sheet『記帳小豬』裡喔！"
        if sheet:
            try:
                records = sheet.get_all_records()
                total = sum([int(r.get('金額',0)) for r in records if str(r.get('金額','')).isdigit()])
                msg = f"📊 目前總記帳 {len(records)} 筆，總金額 {total} 元\n(詳細請看 Google Sheet)"
            except:
                pass
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # 簡易記帳解析
    try:
        parts = text.split()
        if len(parts) >= 2 and parts[-1].replace('$','').replace('元','').isdigit():
            amount = parts[-1].replace('$','').replace('元','')
            category = parts[0]
            add_record(category, amount, text)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🐷 已記 {category} {amount} 元"))
            return
        elif text and any(c.isdigit() for c in text):
            # 抓數字
            import re
            m = re.search(r'(\d+)', text)
            if m:
                amount = m.group(1)
                category = text.replace(amount,'').strip() or "其他"
                add_record(category, amount, text)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🐷 已記 {category} {amount} 元"))
                return
    except:
        pass

    # 預設回覆
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="收到！傳『午餐 120』這樣就能記帳，傳『說明』看教學 🐷"))

@handler.add(MessageEvent)
def handle_follow(event):
    pass

# 處理加好友
@handler.add(MessageEvent, message=TextMessage)
def dummy(): pass

from linebot.models import FollowEvent
@handler.add(FollowEvent)
def handle_follow_event(event):
    try:
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(text=WELCOME_1),
            TextSendMessage(text=WELCOME_2),
            TextSendMessage(text=WELCOME_3)
        ])
    except:
        pass

if __name__ == "__main__":
    app.run()
