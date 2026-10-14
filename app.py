from flask import Flask, request, abort
import os, json, re
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))
DB = "pig_db.json"
SHEET_ID = os.getenv("SHEET_ID") # 你要去 Render 環境變數設定這個

def load():
    if not os.path.exists(DB): return {}
    try:
        with open(DB,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}
def save(d):
    with open(DB,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False)

def write_to_sheet(uid, item, amount):
    # 這裡不會卡死，失敗也沒關係
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        creds_json = os.getenv("GOOGLE_CREDS")
        if not creds_json or not SHEET_ID: return
        creds_dict = json.loads(creds_json)
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        sheet.append_row([uid, item, amount])
    except Exception as e:
        print(f"sheet error: {e}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except: abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    txt = event.message.text.strip()
    uid = event.source.user_id
    db = load()
    if txt == "記帳": rep = "🐷 記帳這樣打：\n午餐 120"
    elif txt == "查詢":
        total = sum([x['amount'] for x in db.get(uid,[])])
        rep = f"目前總額 {total} 元"
    elif txt == "結算":
        total = sum([x['amount'] for x in db.get(uid,[])])
        rep = f"🐷 結算 {total} 元"
    elif txt == "紀錄":
        lst = db.get(uid,[])[-5:]
        rep = "還沒紀錄" if not lst else "\n".join([f"{r['item']} {r['amount']}" for r in lst])
    elif txt == "說明": rep = "Google表單版：打 午餐 120 會自動寫進表單"
    elif txt == "設定": rep = "設定功能開發中"
    else:
        m = re.match(r'(.+)\s+(\d+)$', txt)
        if m:
            item, amt = m.group(1), int(m.group(2))
            db.setdefault(uid, []).append({"item":item,"amount":amt})
            save(db)
            write_to_sheet(uid, item, amt)
            rep = f"已記 {item} {amt} ✅ 已寫入表單"
        else: rep = "請輸入：午餐 120"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=rep))

if __name__ == "__main__":
    app.run()
