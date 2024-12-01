from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
    LocationMessage,
)

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    LocationMessageContent,
)

import os

from modules.reply import faq, menu
from modules.currency import get_exchange_table

from openai import OpenAI
client=OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)



table=get_exchange_table()
print("table",table)

app = Flask(__name__)

# Line Channel 可於 Line Developer Console 申辦
# https://developers.line.biz/en/

# TODO: 填入你的 CHANNEL_SECRET 與 CHANNEL_ACCESS_TOKEN
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN =os.getenv("CHANNEL_ACCESS_TOKEN")

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# @app.route() 用以表達伺服器應用程式路由將會對應到 webhooks 的路徑中
@app.route("/", methods=['POST'])
def callback():
    # ====== 以下為接收並驗證 Line Server 傳來訊息的流程，不需更動 ======
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    # app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("signature驗證錯誤，請檢查Secret與Access Token是否正確...")
        abort(400)
    return 'OK'

# 此處理器負責處理接收到Line Server傳來的文字訊息時的流程
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入文字訊息時
        print("#" * 30)
        line_bot_api = MessagingApi(api_client)
        # event 為 Line Server 傳來的事件物件所有關於一筆訊息的資料皆可從中取得
        # print("event 一個Line文件訊息的事件物件:", event)
        # 在此的 evnet.message.text 即是 Line Server 取得的使用者文字訊息
        user_msg = event.message.text
        print("使用者傳入的文字訊息是:", user_msg)
        # 使用TextMessage產生一段用於回應使用者的Line文字訊息
        bot_msg = TextMessage(text=f"你剛才說的是: {user_msg}")

    #當使用者輸入的文字作為faq的key時，就將value作為bot_msg
        if user_msg in faq:
            bot_msg=faq[user_msg]
        elif user_msg.lower() in ["menu","選單","主選單","首頁"]:
            bot_msg=menu
        elif user_msg in table:
            buy=table[user_msg]["buy"]
            sell=table[user_msg]["sell"]
            bot_msg=TextMessage(text=f"{user_msg}\n買價:{buy}\n賣價:{sell}\n資料來源:以臺灣銀行匯率牌價公告為主")
        else:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """你是一個親切的朋友，可以友善地答覆使用者提供的問題"""},
                    {
                        "role": "user",
                        "content":user_msg
                    }
                ]
            )
            ai_text=completion.choices[0].message.content
            print("AI的回應",ai_text)
            bot_msg=TextMessage(text=ai_text)

            print(completion.choices[0].message)

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                # 放置於 ReplyMessageRequest 的 messages 裡的物件即是要回傳給使用者的訊息
                # 必須注意由於 Line 有其使用的內部格式
                # 因此要回覆的訊息務必使用 Line 官方提供的類別來產生回應物件
                messages=[
                    # 要回應的內容放在這個串列中
                    TextMessage(text="你好 請輸入menu觀看主選單"),
                    bot_msg
                ]
            )
        )

# 此處理器負責處理接收到Line Server傳來的貼圖訊息時的流程
@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入貼圖時
        line_bot_api = MessagingApi(api_client)
        sticker_id = event.message.sticker_id
        package_id = event.message.package_id
        keywords_msg = "這張貼圖背後沒有關鍵字"
        if len(event.message.keywords) > 0:
            keywords_msg = "這張貼圖的關鍵字有:"
            keywords_msg += ", ".join(event.message.keywords)
        # 可以使用的貼圖清單
        # https://developers.line.biz/en/docs/messaging-api/sticker-list/
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    StickerMessage(package_id="6325", sticker_id="10979904"),
                    TextMessage(text=f"你剛才傳入了一張貼圖，以下是這張貼圖的資訊:"),
                    TextMessage(text=f"貼圖包ID為 {package_id} ，貼圖ID為 {sticker_id} 。"),
                    TextMessage(text=keywords_msg),
                ]
            )
        )

# 此處理器負責處理接收到Line Server傳來的地理位置訊息時的流程
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入地理位置時
        line_bot_api = MessagingApi(api_client)
        latitude = event.message.latitude
        longitude = event.message.longitude
        address = event.message.address
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f"You just sent a location message."),
                    TextMessage(text=f"The latitude is {latitude}."),
                    TextMessage(text=f"The longitude is {longitude}."),
                    TextMessage(text=f"The address is {address}."),
                    LocationMessage(title="Here is the location you sent.", address=address, latitude=latitude, longitude=longitude)
                ]
            )
        )

# 如果應用程式被執行執行
if __name__ == "__main__":
    print("[伺服器應用程式開始運行]")
    # 取得遠端環境使用的連接端口，若是在本機端測試則預設開啟於port=5001
    port = int(os.environ.get('PORT', 5001))
    print(f"[Flask即將運行於連接端口:{port}]")
    print(f"若在本地測試請輸入指令開啟測試通道: ./ngrok http {port} ")
    # 啟動應用程式
    # 本機測試使用127.0.0.1, debug=True
    # Heroku or render.com部署使用 0.0.0.0
    app.run(host="0.0.0.0", port=port, debug=True)
