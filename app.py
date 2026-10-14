from flask import Flask, request, abort
import os, json, re, datetime
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, JoinEvent

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

DB_FILE = "pig_db.json"
CATE_FILE = "pig_cate.json"
DEFAULT_CATES = ["飲食","交通","購物","醫療","娛樂","居住","收入"]

WELCOME_1 = """嗨！我是記帳小豬 🐷💰
懶得打開記帳APP？沒關係，直接傳一句「午餐 120」給我，我就幫你記好了！

📒 私訊我 = 你的私人帳本
👫 拉我進群組 = 大家的共同帳本，超適合記情侶帳、室友帳、旅遊帳！

✈️ 旅遊怎麼用？
1. 開一個旅遊群組，把旅伴跟小豬拉進來
2. 誰付錢誰就記一筆「晚餐 3000」
3. 想分錢就打「結算」，小豬自動算出誰要給誰
4. 錢還完打「結清」，下一次重新開始

小提醒：不要把我拉進平常聊天的群組啦，不然「哈哈哈」我也會幫你記喔！"""

WELCOME_2 = """✨ 小豬會做的事
・記帳：午餐 120 / 全聯 1350
・記收入：收入 薪水 50000 / 收入 兼職 3000
・指定分類：醫療 掛號 150 / 交通 捷運 30
・自訂分類：傳「分類」就能新增刪除
・查帳：今天 / 本週 / 本月 / 上月 / 今年
・看最近：傳「最近」看最近5筆
・打錯了：傳「刪除」刪掉最後一筆
・打開雲端帳本：傳「帳本」
・外幣記帳：傳「幣別」看教學
・旅遊分帳：傳「結算」
・分帳歸零：傳「結清」"""

WELCOME_3 = """💡 關於記帳小豬
・完全免費，小豬會努力幫你記帳不偷懶
・你的帳本只有你跟群組成員看得到，小豬不會偷看
・記帳小豬持續進化中，有什麼想加的功能直接跟小豬說「許願」就好！

打「說明」就可以再看一次使用方法喔！"""

def load_db():
    if not os.path.exists(DB_FILE): return []
    try:
        with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return []
def save_db(data):
    with open(DB_FILE,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
def load_cates():
    if not os.path.exists(CATE_FILE): return DEFAULT_CATES.copy()
    try:
        with open(CATE_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return DEFAULT_CATES.copy()
def save_cates(cates):
    with open(CATE_FILE,"w",encoding="utf-8") as f: json.dump(cates,f,ensure_ascii=False)
def write_to_sheet(row):
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        creds_json = os.getenv("GOOGLE_CREDS")
        sheet_id = os.getenv("SHEET_ID")
        if not creds_json or not sheet_id: return
        creds_dict = json.loads(creds_json)
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        sheet.append_row(row)
    except Exception as e:
        print(f"sheet error: {e}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except: abort(400)
    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(event.reply_token, [
        TextSendMessage(text=WELCOME_1),
        TextSendMessage(text=WELCOME_2),
        TextSendMessage(text=WELCOME_3)
    ])

@handler.add(JoinEvent)
def handle_join(event):
    line_bot_api.reply_message(event.reply_token, [
        TextSendMessage(text=WELCOME_1),
        TextSendMessage(text=WELCOME_2),
        TextSendMessage(text=WELCOME_3)
    ])

@handler.add(MessageEvent, message=TextMessage)
def handle(event):
    txt = event.message.text.strip()
    uid = event.source.user_id
    gid = event.source.group_id if event.source.type=='group' else event.source.room_id if event.source.type=='room' else uid
    try:
        profile = line_bot_api.get_profile(uid)
        uname = profile.display_name
    except: uname = "用戶"
    db = load_db()
    cates = load_cates()
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    if txt == "說明": reply = WELCOME_2
    elif txt == "分類":
        reply = f"目前分類：{', '.join(cates)}\n\n新增：分類 新增 孝親\n刪除：分類 刪除 娛樂"
    elif txt.startswith("分類 "):
        parts = txt.split()
        if len(parts)>=3 and parts[1]=="新增":
            new_c = parts[2]
            if new_c not in cates:
                cates.append(new_c); save_cates(cates)
                reply = f"✅ 已新增分類：{new_c}"
            else: reply=f"分類 {new_c} 已存在"
        elif len(parts)>=3 and parts[1]=="刪除":
            del_c = parts[2]
            if del_c in cates:
                cates.remove(del_c); save_cates(cates)
                reply=f"🗑️ 已刪除分類：{del_c}"
            else: reply="找不到此分類"
        else: reply="格式：分類 新增 孝親"
    elif txt == "幣別": reply="出國記外幣：日幣 1000 拉麵 150 / 美金 20 咖啡 150"
    elif txt == "帳本":
        sid = os.getenv("SHEET_ID")
        reply = f"📒 你的帳本：\nhttps://docs.google.com/spreadsheets/d/{sid}" if sid else "帳本已在本地，設定SHEET_ID後會有雲端連結"
    elif txt == "聯絡": reply = WELCOME_3
    elif txt == "許願": reply = "💌 許願收到！小豬會努力進化的～ 你想許什麼功能？"
    elif txt == "刪除":
        recs = [r for r in db if r['gid']==gid and r['uid']==uid]
        if not recs: reply="沒有紀錄可以刪"
        else:
            last = recs[-1]
            db = [r for r in db if r['timestamp']!=last['timestamp']]
            save_db(db)
            reply=f"🗑️ 已刪除：{last.get('cate','')} {last['item']} {last['amount']}"
    elif txt in ["最近","紀錄"]:
        recs = [r for r in db if r['gid']==gid and r['uid']==uid][-5:]
        if not recs: reply="還沒紀錄，快打：午餐 120"
        else: reply="最近5筆：\n"+"\n".join([f"{r['date']} {r.get('cate','')} {r['item']} {r['amount']}" for r in recs])
    elif txt in ["今天","本週","本月","上月","今年","查詢"]:
        if txt=="查詢": txt="本月"
        recs = [r for r in db if r['gid']==gid]
        filtered=[]
        for r in recs:
            try: d=datetime.datetime.strptime(r['date'],"%Y-%m-%d")
            except: continue
            if txt=="今天" and d.date()==now.date(): filtered.append(r)
            elif txt=="本週" and d.isocalendar()[1]==now.isocalendar()[1] and d.year==now.year: filtered.append(r)
            elif txt=="本月" and d.month==now.month and d.year==now.year: filtered.append(r)
            elif txt=="上月":
                lm=now.month-1 if now.month>1 else 12
                ly=now.year if now.month>1 else now.year-1
                if d.month==lm and d.year==ly: filtered.append(r)
            elif txt=="今年" and d.year==now.year: filtered.append(r)
        exp=sum([r['amount'] for r in filtered if r['type']=='expense'])
        inc=sum([r['amount'] for r in filtered if r['type']=='income'])
        reply=f"📊 {txt} 統計：\n支出 {exp} 元\n收入 {inc} 元\n結餘 {inc-exp} 元\n共 {len(filtered)} 筆"
    elif txt=="結算":
        recs=[r for r in db if r['gid']==gid and r['type']=='expense']
        if not recs: reply="還沒支出紀錄"
        else:
            from collections import defaultdict
            total_by=defaultdict(int)
            name_map={}
            for r in recs:
                total_by[r['uid']]+=r['amount']
                name_map[r['uid']]=r.get('uname','用戶')
            total=sum(total_by.values())
            avg=total/len(total_by) if total_by else 0
            lines=[f"總支出 {total} 元，平均每人 {int(avg)} 元"]
            for u,amt in total_by.items():
                diff=amt-avg
                if diff>0: lines.append(f"{name_map[u]} 多付 {int(diff)} 元 (應收)")
                else: lines.append(f"{name_map[u]} 少付 {int(-diff)} 元 (應付)")
            reply="✈️ 旅遊分帳結算：\n"+"\n".join(lines)
    elif txt=="結清":
        db=[r for r in db if r['gid']!=gid]
        save_db(db)
        reply="✅ 已結清！此帳本歸零，下次重新開始"
    else:
        m_inc=re.match(r'^收入\s+(.+)\s+(\d+)$', txt)
        m_cate=re.match(r'^(\S+)\s+(\S+)\s+(\d+)$', txt)
        m_simple=re.match(r'^(.+)\s+(\d+)$', txt)
        record=None
        if m_inc:
            item,amount=m_inc.group(1),int(m_inc.group(2))
            record={"uid":uid,"gid":gid,"uname":uname,"date":today_str,"type":"income","cate":"收入","item":item,"amount":amount,"timestamp":now.isoformat()}
        elif m_cate:
            maybe_cate,item,amount=m_cate.groups()
            if maybe_cate in cates:
                record={"uid":uid,"gid":gid,"uname":uname,"date":today_str,"type":"expense","cate":maybe_cate,"item":item,"amount":int(amount),"timestamp":now.isoformat()}
            elif m_simple:
                item,amount=m_simple.groups()
                record={"uid":uid,"gid":gid,"uname":uname,"date":today_str,"type":"expense","cate":"其他","item":item,"amount":int(amount),"timestamp":now.isoformat()}
        elif m_simple:
            item,amount=m_simple.groups()
            record={"uid":uid,"gid":gid,"uname":uname,"date":today_str,"type":"expense","cate":"其他","item":item,"amount":int(amount),"timestamp":now.isoformat()}
        if record:
            db.append(record); save_db(db)
            write_to_sheet([record['date'], record['gid'], record['uname'], record['type'], record.get('cate',''), record['item'], record['amount']])
            reply=f"🐷 已記 {record.get('cate','')} {record['item']} {record['amount']} 元" if record['type']=='expense' else f"💰 已記收入 {record['item']} {record['amount']} 元"
        else:
            if txt in ["記帳","查詢","結算","紀錄","設定"]:
                reply=WELCOME_2 if txt!="記帳" else "記帳：直接傳 午餐 120"
            else:
                if len(txt)<20:
                    reply="看不懂 🤔 打「說明」看指令\n範例：午餐 120"
                else: return
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run()
