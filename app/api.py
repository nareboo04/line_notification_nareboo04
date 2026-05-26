from fastapi import FastAPI, Request
from app import database as db
from app.line import commands
from app.line import messaging as msg

app = FastAPI(docs_url="/documentation", redoc_url=None)

# Ensure tables exist on startup
db.init_db()


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    for event in body.get("events", []):
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
            msg = event.get("message", {})
            if msg.get("type") == "text":
                text = msg.get("text", "").strip()
                if text:
                    commands.handle(user_id, reply_token, text)

    return {"status": "ok"}


_WELCOME_QR = [
    ("💰 ราคาทอง",     "ราคา ทอง"),
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
        msg.push(user_id, [msg.text_msg(
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
        # Deactivate all alerts for unfollowed user
        cursor.execute("UPDATE alerts SET is_active = 0 WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[webhook] unfollow: {user_id}")
    except Exception as e:
        print(f"[webhook] remove error: {e}")
