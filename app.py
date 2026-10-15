from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.route("/")
def home():
    return "記帳小豬工作中 🐷 Live!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text="嗨！我是記帳小豬 🐷💰\n以後你的每一筆花費我都會幫你記得清清楚楚！"),
            TextSendMessage(text="✨ 小豬會做的事：\n1️⃣ 直接傳『午餐 120』就記帳\n2️⃣ 傳『查詢』看本月花費\n3️⃣ 傳『說明』看完整教學"),
            TextSendMessage(text="快來試試看吧！傳個『午餐 120』給我 🍱")
        ]
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    print(f"收到訊息: {text}")

    # 不管傳什麼，先保證會回！
    if text in ["記帳", "查詢", "結算", "紀錄", "說明"]:
        reply = f"收到！你傳了『{text}』\n\n小豬測試中，先傳『午餐 120』這種有金額的才能真的記帳喔！"
    else:
        reply = f"🐷 已記：{text}\n(測試模式，Google表單串好後就會真的寫入)"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
