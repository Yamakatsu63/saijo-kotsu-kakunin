# インポートするライブラリ
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    FollowEvent, MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ButtonsTemplate, PostbackTemplateAction, MessageTemplateAction, URITemplateAction, PostbackEvent
)
import psycopg2
from psycopg2.extras import DictCursor

import os
import sys
import json
import re

# 軽量なウェブアプリケーションフレームワーク:Flask
app = Flask(__name__)
# 環境変数からLINE Access Tokenを設定
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
# 環境変数からLINE Channel Secretを設定
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# データベースの読み込み
DATABASE_URL = os.environ.get('HEROKU_POSTGRESQL_ONYX_URL')


@app.route('/')
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Follow Event


@handler.add(FollowEvent)
def on_follow(event):
    reply_token = event.reply_token
    user_id = event.source.user_id
    profiles = line_bot_api.get_profile(user_id=user_id)
    display_name = profiles.display_name

    # DBへの保存
    try:
        conn = psycopg2.connect(DATABASE_URL)
        c = conn.cursor()
        sql = "SELECT name FROM user_data WHERE id = '"+user_id+"';"
        c.execute(sql)
        ret = c.fetchall()
        if len(ret) == 0:
            sql = "INSERT INTO user_data (id, name) VALUES ('" + \
                user_id+"', '"+str(display_name)+"');"
        elif len(ret) == 1:
            sql = "UPDATE user_data SET name = " + \
                str(display_name) + "WHERE id = '"+user_id+"';"
        c.execute(sql)
        conn.commit()
    finally:
        conn.close()
        c.close()

    # メッセージの送信
    line_bot_api.reply_message(
        reply_token=reply_token,
        messages=TextSendMessage(text='友達追加ありがとう！')
    )


@handler.add(PostbackEvent)
# MessageEvent
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 時刻表と入力されたら画像を送信する
    if event.message.text == "時刻表":
        image_message = ImageSendMessage(
            original_content_url=f"https://linebot-practice-12.herokuapp.com/static/jikokuhyou.jpg",
            preview_image_url=f"https://linebot-practice-12.herokuapp.com/static/jikokuhyou.jpg",
        )
        line_bot_api.reply_message(
            event.reply_token,
            image_message
        )
    else:
        # 出発時間が送られたら5件出力する
        m = re.match(r'^([01][0-9]|2[0-3]):[0-5][0-9]$', event.message.text)
        conn = psycopg2.connect(DATABASE_URL)
        c = conn.cursor()
        if m != None:
            sql = "SELECT departure_time, arrival_time FROM jikokuhyou WHERE departure_time > '" + \
                m.group(0)+"' limit 5;"
            c.execute(sql)
            ret = c.fetchall()

            line_bot_api.reply_message(
                event.reply_token,
                messages=TemplateSendMessage(
                    alt_text="時刻検索結果",
                    template=ButtonsTemplate(
                        text="バス時刻表検索",
                        actions=[
                            PostbackTemplateAction(
                                label=ret[0][0].strftime(
                                    "%H:%M") + "発 " + ret[0][1].strftime("%H:%M") + "着",
                                data="is_show=0"
                            ),
                            PostbackTemplateAction(
                                label=ret[1][0].strftime(
                                    "%H:%M") + "発 " + ret[1][1].strftime("%H:%M") + "着",
                                data="is_show=1"
                            ),

                            PostbackTemplateAction(
                                label=ret[2][0].strftime(
                                    "%H:%M") + "発 " + ret[2][1].strftime("%H:%M") + "着",
                                data="is_show=2"
                            ),
                            PostbackTemplateAction(
                                label=ret[3][0].strftime(
                                    "%H:%M") + "発 " + ret[3][1].strftime("%H:%M") + "着",
                                data="is_show=3"
                            )
                        ]
                    )
                )
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="出発したい時間を入力してください！\nその後の直近５件の時刻を教えます。\n(例)09:00, 12:00, 15:30")
            )


if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
