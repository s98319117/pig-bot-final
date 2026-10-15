
import os, json, time
from flask import Flask, request, redirect, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ButtonComponent, URIAction
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# LINE
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# Google OAuth 設定
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
REDIRECT_URI = "https://pig-bot-final.onrender.com/auth/callback"

# 簡易儲存 (Render 重開會不見，但夠測試，正式可用資料庫)
TOKENS_FILE = "/tmp/tokens.json"
def load_tokens():
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, 'r') as f:
                return json.load(f)
        except: return {}
    return {}

def save_tokens(data):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(data, f)

def get_flow(state=None):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = REDIRECT_URI
    return flow

@app.route("/")
def home():
    return "記帳小豬工作中 🐷 Live! OAuth版"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- OAuth 開始 ---
@app.route("/auth/login")
def auth_login():
    uid = request.args.get("uid")
    if not uid:
        return "缺少 uid", 400
    flow = get_flow(state=uid)
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    return redirect(auth_url)

@app.route("/auth/callback")
def auth_callback():
    uid = request.args.get("state")
    flow = get_flow(state=uid)
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    
    tokens = load_tokens()
    tokens[uid] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }
    save_tokens(tokens)

    # 自動幫使用者建一張表
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet_body = {
            'properties': {'title': f'記帳小豬 - {time.strftime("%Y-%m-%d")}'},
            'sheets': [{'properties': {'title': '記帳紀錄'}}]
        }
        result = service.spreadsheets().create(body=sheet_body).execute()
        sheet_id = result.get('spreadsheetId')
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        
        # 寫入標題
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='記帳紀錄!A1:E1',
            valueInputOption='RAW',
            body={'values': [['日期', '項目', '金額', '分類', '記帳人']]}
        ).execute()

        # 儲存 sheet_id
        tokens[uid]['sheet_id'] = sheet_id
        tokens[uid]['sheet_url'] = sheet_url
        save_tokens(tokens)
        
        # 推播成功訊息給 LINE 使用者
        line_bot_api.push_message(uid, TextSendMessage(text=f"✅ 連結成功！\n你的帳本已經建在你的 Google 雲端硬碟了！\n\n{sheet_url}\n\n快傳「午餐 120」試試看！"))
        
        return f"<h1>連結成功！</h1><p>帳本已建立：<a href='{sheet_url}'>{sheet_url}</a></p><p>請回到 LINE 開始記帳！</p>"
    except Exception as e:
        print(f"建表失敗: {e}")
        line_bot_api.push_message(uid, TextSendMessage(text=f"連結成功，但建表失敗：{e}"))
        return f"連結成功但建表失敗: {e}"

def get_user_creds(uid):
    tokens = load_tokens()
    data = tokens.get(uid)
    if not data:
        return None
    return Credentials(
        token=data['token'],
        refresh_token=data.get('refresh_token'),
        token_uri=data['token_uri'],
        client_id=data['client_id'],
        client_secret=data['client_secret'],
        scopes=data['scopes']
    )

def send_link_button(reply_token, uid):
    link_url = f"https://pig-bot-final.onrender.com/auth/login?uid={uid}"
    bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='點下方按鈕，用你的 Google 帳號登入，帳本會建在你的 Google 雲端硬碟。(連結 30 分鐘內有效)', wrap=True, size='md')
            ]
        ),
        footer=BoxComponent(
            layout='vertical',
            contents=[
                ButtonComponent(style='primary', action=URIAction(label='連結 Google 帳號', uri=link_url))
            ]
        )
    )
    line_bot_api.reply_message(reply_token, FlexSendMessage(alt_text='請連結 Google 帳號', contents=bubble))

@handler.add(FollowEvent)
def handle_follow(event):
    uid = event.source.user_id
    tokens = load_tokens()
    if uid not in tokens:
        send_link_button(event.reply_token, uid)
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="嗨！我是記帳小豬 🐷\n你已經連結過了，快傳「午餐 120」記帳！"))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    uid = event.source.user_id
    text = event.message.text.strip()
    
    tokens = load_tokens()
    if uid not in tokens:
        send_link_button(event.reply_token, uid)
        return

    # 已連結，處理記帳
    if text in ["說明", "help"]:
        msg = "✨ 我會做的事\n• 記帳：午餐 120、全聯 1350\n• 收入：收入 薪水 50000\n• 查詢：今天 / 本週 / 本月\n• 最近：傳「最近」看5筆\n• 刪除：傳「刪除」刪最後一筆\n• 帳本：傳「帳本」開你的表\n• 結算：自動算誰該給誰多少"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text in ["帳本"]:
        sheet_url = tokens[uid].get('sheet_url', '找不到')
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你的帳本：\n{sheet_url}"))
        return

    # 簡易記帳解析
    try:
        creds_data = tokens[uid]
        creds = get_user_creds(uid)
        # refresh token if needed
        from google.auth.transport.requests import Request
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            creds_data['token'] = creds.token
            tokens[uid] = creds_data
            save_tokens(tokens)
        
        service = build('sheets', 'v4', credentials=creds)
        sheet_id = creds_data.get('sheet_id')
        
        # 解析金額
        import re
        m = re.search(r'(\d+)', text)
        if m:
            amount = m.group(1)
            item = text.replace(amount, '').strip() or '記帳'
            row = [[time.strftime('%Y-%m-%d %H:%M'), item, amount, '未分類', uid[:5]]]
            service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='記帳紀錄!A:E',
                valueInputOption='RAW',
                body={'values': row}
            ).execute()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🐷 已記：{item} {amount} 元\n已寫入你的 Google 表單！"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"收到「{text}」\n請傳「午餐 120」這種有數字的才會記帳喔！"))
    except Exception as e:
        print(f"記帳錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"記帳失敗：{e}\n請重新點選單連結 Google 帳號"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
