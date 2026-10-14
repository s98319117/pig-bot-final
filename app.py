from flask import Flask, request, abort
import os, json, re, datetime
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
        with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}
def save_db(d):
    with open(DB_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except: abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle(event):
    text=event.message.text.strip()
    uid=event.source.user_id
    db=load_db()
    if text=="記帳": reply="記帳：直接傳 午餐 120"
    elif text=="查詢":
        total=sum([x['amount'] for x in db.get(uid,[])])
        reply=f"目前總額 {total} 元"
    elif text=="結算":
        total=sum([x['amount'] for x in db.get(uid,[])])
        reply=f"結算 {total} 元"
    elif text=="紀錄":
        rec=db.get(uid,[])[-5:]
        reply="沒紀錄" if not rec else "\n".join([f"{r['item']} {r['amount']}" for r in rec])
    elif text=="說明": reply="輸入：品項 金額，例如 午餐 120"
    elif text=="設定": reply="設定功能開發中"
    else:
        m=re.match(r'(.+)\s+(\d+)$',text)
        if m:
            item,amount=m.group(1),int(m.group(2))
            db.setdefault(uid,[]).append({"item":item,"amount":amount})
            save_db(db)
            reply=f"已記 {item} {amount}"
        else: reply="請輸入 午餐 120 或按選單"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__=="__main__": app.run()
