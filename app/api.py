import hashlib
import hmac
import base64
import json

from fastapi import FastAPI, Request, HTTPException
from app import database as db
from app.line import commands
from app.line import messaging as messaging
from app.config import LINE_CHANNEL_SECRET

app = FastAPI(docs_url=None, redoc_url=None)

db.init_db()


def _verify_signature(body: bytes, sig: str) -> bool:
    if not LINE_CHANNEL_SECRET:
        return True  # skip in dev if secret not set
    expected = base64.b64encode(
        hmac.new(LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(sig, expected)


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    sig  = request.headers.get("X-Line-Signature", "")

    if not _verify_signature(body, sig):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(body)

    for event in data.get("events", []):
        event_type  = event.get("type")
        reply_token = event.get("replyToken", "")
        source      = event.get("source", {})
        user_id     = source.get("userId")

        if not user_id:
            continue

        if event_type == "follow":
            _register_user(user_id)
        elif event_type == "unfollow":
            _remove_user(user_id)
        elif event_type == "message":
            line_msg = event.get("message", {})
            if line_msg.get("type") == "text":
                text = line_msg.get("text", "").strip()
                if text:
                    commands.handle(user_id, reply_token, text)

    return {"status": "ok"}


_WELCOME_QR = [
    ("💰 ราคาทอง",      "ราคา ทอง"),
    ("❓ คำสั่งทั้งหมด", "ช่วยเหลือ"),
]


def _register_user(user_id: str):
    try:
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO users (user_id) VALUES (%s)", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[webhook] follow: {user_id}")
        messaging.push(user_id, [messaging.text_msg(
            "ยินดีต้อนรับ! 🎉\n\n"
            "บอทนี้แจ้งเตือนราคา ทองคำ / หุ้น / คริปโต ได้เลย\n"
            "พิมพ์ 'ช่วยเหลือ' เพื่อดูคำสั่งทั้งหมด",
            _WELCOME_QR,
        )])
    except Exception as e:
        print(f"[webhook] register error: {e}")


def _remove_user(user_id: str):
    try:
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE alerts SET is_active = 0 WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE scheduled_alerts SET is_active = 0 WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[webhook] unfollow: {user_id}")
    except Exception as e:
        print(f"[webhook] remove error: {e}")
