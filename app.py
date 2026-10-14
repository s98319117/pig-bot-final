from flask import Flask, request, abort
import os, json, datetime
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

CHANNEL_SECRET = os.getenv("CHANNEL_SECRET", "3d1a4d67b1437dbdaa12efd37852221be")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

DB_FILE = "pig_db.json"
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else event.source.user_id
    import re
    m = re.search(r"(\d+)", text)
    if m and any(x in text for x in ["查帳","誰欠誰","結算","最近","一個月","三個月","一年","使用說明"])==False:
        amount = int(m.group(1))
        desc = text.replace(m.group(1), "").strip() or "未命名"
        db = load_db()
        if group_id not in db: db[group_id]=[]
        db[group_id].append({"date": datetime.datetime.now().isoformat(),"amount": amount,"desc": desc})
        save_db(db)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 已記：{desc} {amount}元"))
        return
    if "查帳" in text or "誰欠誰" in text:
        db=load_db(); recs=db.get(group_id,[]); total=sum(r["amount"] for r in recs)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🐷 小豬報告\n總花費：{total}元\n平均每人：{total//2 if total else 0}元"))
        return
    if "最近" in text:
        db=load_db(); recs=db.get(group_id,[])[-5:]
        if not recs: line_bot_api.reply_message(event.reply_token, TextSendMessage(text="還沒有紀錄，傳「午餐 120」試試！")); return
        lines=["📝 最近5筆："]+[f"{r['desc']} {r['amount']}元" for r in recs[::-1]]
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="\n".join(lines))); return
    if "使用說明" in text:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="傳「午餐 120」就能記帳，點「誰欠誰」看結算！")); return
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="收到！傳「午餐 120」就能記帳"))

@app.route("/")
def home():
    return "🐷 小豬分帳 已上線！"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
