from flask import Flask, request, abort
import os, json, datetime, re
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

DB_FILE = "pig_db.json"
def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    db = load_db()

    # --- 選單功能 ---
    if text == "記帳":
        reply = "🐷 記帳這樣打：\n例如：午餐 120\n例如：飲料 60"
    elif text == "查詢":
        total = sum([v['amount'] for v in db.get(user_id, [])])
        reply = f"📊 目前總共記了 {total} 元"
    elif text == "結算":
        total = sum([v['amount'] for v in db.get(user_id, [])])
        reply = f"🧮 結算：總共 {total} 元\n輸入「清空」可重來"
    elif text == "紀錄":
        records = db.get(user_id, [])[-5:]
        if not records: reply = "還沒有紀錄喔"
        else:
            reply = "📜 最近5筆：\n" + "\n".join([f"{r['item']} {r['amount']}" for r in records])
    elif text == "說明":
        reply = "🐷 小豬分帳說明\n1. 輸入：品項 金額 (午餐 120)\n2. 按選單快速操作\n3. 所有紀錄會存在 Google 表單"
    elif text == "設定":
        reply = "⚙️ 設定：目前沒有設定，之後會開放改名字功能！"
    elif text == "清空":
        db[user_id] = []
        save_db(db)
        reply = "🗑️ 已清空所有紀錄"
    else:
        # 原本的記帳邏輯：最後一個字是數字的
        m = re.match(r'(.+?)\s+(\d+)$', text)
        if m:
            item, amount = m.group(1), int(m.group(2))
            if user_id not in db: db[user_id] = []
            db[user_id].append({"item": item, "amount": amount, "time": datetime.datetime.now().strftime("%m/%d")})
            save_db(db)
            reply = f"✅ 已記：{item} {amount}元"
            # Google Sheet 這裡先省略，先讓本地能動
        else:
            reply = "收到！傳「午餐 120」就能記帳\n按下方選單也可以喔"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run()
