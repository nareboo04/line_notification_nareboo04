"""
LINE command parser and handler.

Price commands:
  ราคา ทอง
  ราคา หุ้น [SYMBOL]           → Thai stock (SET)
  ราคา หุ้นอเมริกา [SYMBOL]    → US stock
  ราคา คริปโต [SYMBOL]

Price alert commands:
  แจ้งเตือน ทอง [ราคา]
  แจ้งเตือน ทอง สูงกว่า/ต่ำกว่า [ราคา]
  แจ้งเตือน หุ้น [SYM] [ราคา]
  แจ้งเตือน หุ้นอเมริกา [SYM] [ราคา]
  แจ้งเตือน คริปโต [SYM] [ราคา]

Schedule alert commands:
  แจ้งเตือนเวลา ทอง 09:00
  แจ้งเตือนเวลา ทอง 09:00 วันธรรมดา
  แจ้งเตือนเวลา หุ้น PTT 09:30
  แจ้งเตือนเวลา หุ้นอเมริกา AAPL 16:00
  แจ้งเตือนเวลา คริปโต BTC 08:00 วันหยุด

Management:
  ดูแจ้งเตือน          → price alerts
  ดูแจ้งเตือนเวลา       → schedule alerts
  ลบแจ้งเตือน [id]
  ลบแจ้งเตือนเวลา [id]
  ลบแจ้งเตือนทั้งหมด
  ช่วยเหลือ
"""

import re
from app import database as db
from app.line import messaging as msg
from app.scrapers import gold, stock, crypto
from app.scrapers.crypto import SUPPORTED as CRYPTO_SUPPORTED


# ── Keyword sets ────────────────────────────────────────────────────────────────

_CMD_PRICE       = {"ราคา", "price", "เช็คราคา", "ดูราคา", "ขอราคา", "เช็ค"}
_CMD_ALERT       = {"แจ้งเตือน", "alert", "ตั้งแจ้งเตือน", "notify"}
_CMD_ALERT_SCHED = {"แจ้งเตือนเวลา", "alerttime", "ตั้งเวลาแจ้งเตือน", "ตั้งเวลา"}
_CMD_LIST_PRICE  = {"ดูแจ้งเตือน", "alerts", "รายการแจ้งเตือน"}
_CMD_LIST_SCHED  = {"ดูแจ้งเตือนเวลา", "schedules", "รายการเวลา"}
_CMD_DEL_PRICE   = {"ลบแจ้งเตือน", "deletealert"}
_CMD_DEL_SCHED   = {"ลบแจ้งเตือนเวลา", "deleteschedule"}
_CMD_HELP        = {"ช่วยเหลือ", "help", "วิธีใช้", "คำสั่ง", "เมนู", "menu", "?", "/?"}

_ASSET_GOLD      = {"ทอง", "gold", "ทองคำ", "โกลด์", "xau", "gg"}
_ASSET_STOCK_TH  = {"หุ้น", "stock", "หุ้นไทย", "หลักทรัพย์", "set", "mai", "ตลาดหุ้น"}
_ASSET_STOCK_US  = {
    "หุ้นอเมริกา", "หุ้นus", "หุ้นต่างประเทศ", "หุ้นนอก", "หุ้นusd", "us", "อเมริกา",
    "หุ้นเมกา", "เมกา", "หุ้นอเมริกัน", "หุ้นฝรั่ง", "nasdaq", "nyse", "หุ้นดาว", "หุ้นนาสแด็ก",
}
_ASSET_CRYPTO    = {"คริปโต", "crypto", "คริปต์", "cryptocurrency", "คอยน์", "coin", "เหรียญ", "บิท"}

_COND_ABOVE      = {"สูงกว่า", "มากกว่า", "above", ">", ">="}
_COND_BELOW      = {"ต่ำกว่า", "น้อยกว่า", "below", "<", "<="}

_DAYS_DAILY      = {"ทุกวัน", "daily", "ทุกๆวัน"}
_DAYS_WEEKDAY    = {"วันธรรมดา", "วันทำงาน", "weekday", "จันทร์-ศุกร์"}
_DAYS_WEEKEND    = {"วันหยุด", "เสาร์อาทิตย์", "weekend", "วันเสาร์อาทิตย์"}


# ── Entry point ─────────────────────────────────────────────────────────────────

def handle(user_id: str, reply_token: str, text: str):
    parts = text.strip().split()
    if not parts:
        return

    cmd = parts[0].lower()

    if cmd in _CMD_PRICE:
        _cmd_price(user_id, reply_token, parts)
    elif cmd in _CMD_ALERT_SCHED:
        _cmd_set_schedule(user_id, reply_token, parts)
    elif cmd in _CMD_ALERT:
        _cmd_set_alert(user_id, reply_token, parts)
    elif cmd in _CMD_LIST_SCHED:
        _cmd_list_schedules(user_id, reply_token)
    elif cmd in _CMD_LIST_PRICE:
        _cmd_list_alerts(user_id, reply_token)
    elif cmd in _CMD_DEL_SCHED or "ลบแจ้งเตือนเวลา" in text:
        _cmd_delete_schedule(user_id, reply_token, parts)
    elif cmd in _CMD_DEL_PRICE or "ลบแจ้งเตือนทั้งหมด" in text:
        _cmd_delete_alert(user_id, reply_token, parts, text)
    elif cmd in _CMD_HELP:
        _cmd_help(reply_token)
    else:
        msg.reply(reply_token, [msg.text_msg(
            "ไม่รู้จักคำสั่งนี้ 🤔\nพิมพ์ 'ช่วยเหลือ' เพื่อดูคำสั่งทั้งหมด"
        )])


# ── Price display ────────────────────────────────────────────────────────────────

def _cmd_price(user_id: str, reply_token: str, parts: list[str]):
    if len(parts) == 1 or (len(parts) >= 2 and parts[1].lower() in _ASSET_GOLD):
        data = gold.fetch()
        if data:
            msg.reply(reply_token, [msg.flex_msg("ราคาทองคำ", msg.build_gold_bubble(data))])
        else:
            msg.reply(reply_token, [msg.text_msg("ดึงราคาทองไม่ได้ในขณะนี้ ลองใหม่อีกครั้ง")])
        return

    if len(parts) >= 2:
        asset_word = parts[1].lower()

        if asset_word in _ASSET_STOCK_TH:
            _price_stock(user_id, reply_token, parts[2:], market="TH")
            return

        if asset_word in _ASSET_STOCK_US:
            _price_stock(user_id, reply_token, parts[2:], market="US")
            return

        if asset_word in _ASSET_CRYPTO:
            if len(parts) < 3:
                msg.reply(reply_token, [msg.text_msg(
                    f"ระบุชื่อเหรียญ เช่น: ราคา คริปโต BTC\n"
                    f"เหรียญที่รองรับ: {', '.join(CRYPTO_SUPPORTED)}"
                )])
                return
            sym = parts[2].upper()
            data = crypto.fetch(sym)
            if data:
                msg.reply(reply_token, [msg.flex_msg(f"ราคา {sym}", msg.build_crypto_bubble(data))])
            else:
                msg.reply(reply_token, [msg.text_msg(
                    f"ไม่รองรับเหรียญ '{sym}'\nเหรียญที่รองรับ: {', '.join(CRYPTO_SUPPORTED)}"
                )])
            return

    msg.reply(reply_token, [msg.text_msg(
        "รูปแบบ:\n• ราคา ทอง\n• ราคา หุ้น PTT\n• ราคา หุ้นอเมริกา AAPL\n• ราคา คริปโต BTC"
    )])


def _price_stock(user_id: str, reply_token: str, sym_parts: list[str], market: str):
    if not sym_parts:
        example = "PTT" if market == "TH" else "AAPL"
        label = "หุ้น" if market == "TH" else "หุ้นอเมริกา"
        msg.reply(reply_token, [msg.text_msg(f"ระบุชื่อหุ้น เช่น: ราคา {label} {example}")])
        return
    sym = sym_parts[0].upper()
    msg.reply(reply_token, [msg.text_msg(f"⏳ กำลังดึงราคา {sym}...")])
    data = stock.fetch(sym, market)
    if data:
        msg.push(user_id, [msg.flex_msg(f"ราคาหุ้น {data.symbol}", msg.build_stock_bubble(data))])
    else:
        msg.push(user_id, [msg.text_msg(
            f"ไม่พบข้อมูล '{sym}'\n"
            + ("ตรวจสอบชื่อย่อหุ้น SET เช่น PTT, SCB, KBANK"
               if market == "TH" else
               "ตรวจสอบชื่อย่อหุ้น US เช่น AAPL, TSLA, NVDA")
        )])


# ── Price alerts ─────────────────────────────────────────────────────────────────

def _cmd_set_alert(user_id: str, reply_token: str, parts: list[str]):
    if len(parts) < 3:
        msg.reply(reply_token, [msg.text_msg(
            "รูปแบบ: แจ้งเตือน [สินทรัพย์] [ราคา]\n"
            "เช่น: แจ้งเตือน ทอง 45000\n"
            "เช่น: แจ้งเตือน หุ้นอเมริกา AAPL สูงกว่า 200"
        )])
        return

    asset_word = parts[1].lower()

    if asset_word in _ASSET_GOLD:
        _save_price_alert(user_id, reply_token, "gold", None, "TH", parts[2:])
    elif asset_word in _ASSET_STOCK_TH:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือน หุ้น [ชื่อหุ้น] [ราคา]")])
            return
        _save_price_alert(user_id, reply_token, "stock", parts[2].upper(), "TH", parts[3:])
    elif asset_word in _ASSET_STOCK_US:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือน หุ้นอเมริกา [ชื่อหุ้น] [ราคา]")])
            return
        _save_price_alert(user_id, reply_token, "stock", parts[2].upper(), "US", parts[3:])
    elif asset_word in _ASSET_CRYPTO:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือน คริปโต [ชื่อเหรียญ] [ราคา]")])
            return
        sym = parts[2].upper()
        if sym not in CRYPTO_SUPPORTED:
            msg.reply(reply_token, [msg.text_msg(
                f"ไม่รองรับ '{sym}'\nเหรียญที่รองรับ: {', '.join(CRYPTO_SUPPORTED)}"
            )])
            return
        _save_price_alert(user_id, reply_token, "crypto", sym, "TH", parts[3:])
    else:
        msg.reply(reply_token, [msg.text_msg(
            "ระบุสินทรัพย์: ทอง / หุ้น / หุ้นอเมริกา / คริปโต"
        )])


def _save_price_alert(user_id: str, reply_token: str, asset_type: str,
                      symbol: str | None, market: str, remaining: list[str]):
    condition: str | None = None
    price_str: str | None = None

    if len(remaining) == 1:
        price_str = remaining[0]
    elif len(remaining) == 2:
        word = remaining[0].lower()
        if word in _COND_ABOVE:
            condition = "above"
        elif word in _COND_BELOW:
            condition = "below"
        else:
            msg.reply(reply_token, [msg.text_msg(
                f"เงื่อนไข '{remaining[0]}' ไม่รู้จัก ใช้ 'สูงกว่า' หรือ 'ต่ำกว่า'"
            )])
            return
        price_str = remaining[1]
    else:
        msg.reply(reply_token, [msg.text_msg("รูปแบบไม่ถูกต้อง พิมพ์ 'ช่วยเหลือ' เพื่อดูตัวอย่าง")])
        return

    try:
        target = float(price_str.replace(",", ""))
        if target <= 0:
            raise ValueError
    except ValueError:
        msg.reply(reply_token, [msg.text_msg(f"ราคา '{price_str}' ไม่ถูกต้อง")])
        return

    if condition is None:
        current = _get_current_price(asset_type, symbol, market)
        if current is None:
            msg.reply(reply_token, [msg.text_msg("ดึงราคาปัจจุบันไม่ได้ ลองใหม่อีกครั้ง")])
            return
        if abs(current - target) / target < 0.005:
            msg.reply(reply_token, [msg.text_msg(
                f"ราคาปัจจุบัน ({current:,.2f}) ใกล้เคียงกับเป้าหมายมาก\n"
                "กรุณาระบุ 'สูงกว่า' หรือ 'ต่ำกว่า'"
            )])
            return
        condition = "above" if current < target else "below"

    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO alerts (user_id, asset_type, asset_symbol, asset_market, target_price, condition_type) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, asset_type, symbol, market, target, condition),
    )
    alert_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    asset_label = _asset_label(asset_type, symbol, market)
    cond_label  = "สูงกว่าหรือเท่ากับ" if condition == "above" else "ต่ำกว่าหรือเท่ากับ"

    msg.reply(reply_token, [msg.text_msg(
        f"✅ ตั้งแจ้งเตือนราคา #{alert_id} สำเร็จ!\n\n"
        f"สินทรัพย์ : {asset_label}\n"
        f"เงื่อนไข  : {cond_label}\n"
        f"ราคา      : {target:,.2f}\n\n"
        "จะแจ้งเตือนทันทีเมื่อราคาถึงเป้าหมาย 🔔"
    )])


def _cmd_list_alerts(user_id: str, reply_token: str):
    conn = db.get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, asset_type, asset_symbol, asset_market, target_price, condition_type "
        "FROM alerts WHERE user_id = %s AND is_active = 1 ORDER BY id",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        msg.reply(reply_token, [msg.text_msg("ไม่มีแจ้งเตือนราคาที่ตั้งไว้ 📋")])
        return

    cond_labels = {"above": "สูงกว่า", "below": "ต่ำกว่า"}
    lines = [f"📋 แจ้งเตือนราคา ({len(rows)} รายการ)\n"]
    for r in rows:
        label = _asset_label(r["asset_type"], r["asset_symbol"], r.get("asset_market", "TH"))
        cond  = cond_labels[r["condition_type"]]
        price = float(r["target_price"])
        lines.append(f"#{r['id']} {label} → {cond} {price:,.2f}")

    lines.append("\nพิมพ์ 'ลบแจ้งเตือน [หมายเลข]' เพื่อลบ")
    msg.reply(reply_token, [msg.text_msg("\n".join(lines))])


def _cmd_delete_alert(user_id: str, reply_token: str, parts: list[str], full_text: str):
    if "ทั้งหมด" in full_text:
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET is_active = 0 WHERE user_id = %s AND is_active = 1", (user_id,))
        n1 = cursor.rowcount
        cursor.execute("UPDATE scheduled_alerts SET is_active = 0 WHERE user_id = %s AND is_active = 1", (user_id,))
        n2 = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        msg.reply(reply_token, [msg.text_msg(
            f"🗑️ ลบแจ้งเตือนทั้งหมดแล้ว\n"
            f"• ราคา: {n1} รายการ\n• เวลา: {n2} รายการ"
        )])
        return

    if len(parts) < 2:
        msg.reply(reply_token, [msg.text_msg("ระบุหมายเลข เช่น: ลบแจ้งเตือน 3")])
        return
    try:
        alert_id = int(parts[1])
    except ValueError:
        msg.reply(reply_token, [msg.text_msg(f"หมายเลข '{parts[1]}' ไม่ถูกต้อง")])
        return

    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE alerts SET is_active = 0 WHERE id = %s AND user_id = %s AND is_active = 1",
        (alert_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if affected:
        msg.reply(reply_token, [msg.text_msg(f"🗑️ ลบแจ้งเตือนราคา #{alert_id} แล้ว")])
    else:
        msg.reply(reply_token, [msg.text_msg(f"ไม่พบแจ้งเตือน #{alert_id}")])


# ── Schedule alerts ──────────────────────────────────────────────────────────────

def _cmd_set_schedule(user_id: str, reply_token: str, parts: list[str]):
    # แจ้งเตือนเวลา ทอง 09:00
    # แจ้งเตือนเวลา หุ้น PTT 09:30 วันธรรมดา
    # แจ้งเตือนเวลา หุ้นอเมริกา AAPL 16:00
    # แจ้งเตือนเวลา คริปโต BTC 08:00 วันหยุด

    if len(parts) < 3:
        msg.reply(reply_token, [msg.text_msg(
            "รูปแบบ: แจ้งเตือนเวลา [สินทรัพย์] [เวลา]\n"
            "เช่น: แจ้งเตือนเวลา ทอง 09:00\n"
            "เช่น: แจ้งเตือนเวลา หุ้น PTT 09:30 วันธรรมดา"
        )])
        return

    asset_word = parts[1].lower()

    if asset_word in _ASSET_GOLD:
        _save_schedule(user_id, reply_token, "gold", None, "TH", parts[2:])
    elif asset_word in _ASSET_STOCK_TH:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือนเวลา หุ้น [ชื่อหุ้น] [เวลา]")])
            return
        _save_schedule(user_id, reply_token, "stock", parts[2].upper(), "TH", parts[3:])
    elif asset_word in _ASSET_STOCK_US:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือนเวลา หุ้นอเมริกา [ชื่อหุ้น] [เวลา]")])
            return
        _save_schedule(user_id, reply_token, "stock", parts[2].upper(), "US", parts[3:])
    elif asset_word in _ASSET_CRYPTO:
        if len(parts) < 4:
            msg.reply(reply_token, [msg.text_msg("รูปแบบ: แจ้งเตือนเวลา คริปโต [ชื่อเหรียญ] [เวลา]")])
            return
        sym = parts[2].upper()
        if sym not in CRYPTO_SUPPORTED:
            msg.reply(reply_token, [msg.text_msg(
                f"ไม่รองรับ '{sym}'\nเหรียญที่รองรับ: {', '.join(CRYPTO_SUPPORTED)}"
            )])
            return
        _save_schedule(user_id, reply_token, "crypto", sym, "TH", parts[3:])
    else:
        msg.reply(reply_token, [msg.text_msg(
            "ระบุสินทรัพย์: ทอง / หุ้น / หุ้นอเมริกา / คริปโต"
        )])


def _save_schedule(user_id: str, reply_token: str, asset_type: str,
                   symbol: str | None, market: str, remaining: list[str]):
    # remaining: ['09:00'] | ['09:00', 'วันธรรมดา']
    if not remaining:
        msg.reply(reply_token, [msg.text_msg("ระบุเวลา เช่น 09:00")])
        return

    time_str = _parse_time(remaining[0])
    if time_str is None:
        msg.reply(reply_token, [msg.text_msg(
            f"เวลา '{remaining[0]}' ไม่ถูกต้อง\nรูปแบบที่รองรับ: 09:00, 9:30, 16:00"
        )])
        return

    # Optional day specification
    schedule_days = "daily"
    if len(remaining) >= 2:
        day_word = remaining[1].lower()
        if day_word in _DAYS_WEEKDAY:
            schedule_days = "weekday"
        elif day_word in _DAYS_WEEKEND:
            schedule_days = "weekend"
        elif day_word in _DAYS_DAILY:
            schedule_days = "daily"
        else:
            msg.reply(reply_token, [msg.text_msg(
                f"ไม่รู้จักวัน '{remaining[1]}'\n"
                "ใช้: ทุกวัน / วันธรรมดา / วันหยุด"
            )])
            return

    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scheduled_alerts "
        "(user_id, asset_type, asset_symbol, asset_market, schedule_time, schedule_days) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, asset_type, symbol, market, time_str, schedule_days),
    )
    sched_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    days_label = {"daily": "ทุกวัน", "weekday": "วันธรรมดา (จ-ศ)", "weekend": "วันหยุด (ส-อ)"}
    asset_label = _asset_label(asset_type, symbol, market)

    msg.reply(reply_token, [msg.text_msg(
        f"✅ ตั้งแจ้งเตือนเวลา #{sched_id} สำเร็จ!\n\n"
        f"สินทรัพย์ : {asset_label}\n"
        f"เวลา      : {time_str} น.\n"
        f"วัน       : {days_label[schedule_days]}\n\n"
        "จะส่งราคาให้ตามเวลาที่ตั้งไว้ 🕐"
    )])


def _cmd_list_schedules(user_id: str, reply_token: str):
    conn = db.get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, asset_type, asset_symbol, asset_market, schedule_time, schedule_days "
        "FROM scheduled_alerts WHERE user_id = %s AND is_active = 1 ORDER BY schedule_time",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        msg.reply(reply_token, [msg.text_msg("ไม่มีแจ้งเตือนตามเวลาที่ตั้งไว้ 🕐")])
        return

    days_labels = {"daily": "ทุกวัน", "weekday": "จ-ศ", "weekend": "ส-อ"}
    lines = [f"🕐 แจ้งเตือนตามเวลา ({len(rows)} รายการ)\n"]
    for r in rows:
        label = _asset_label(r["asset_type"], r["asset_symbol"], r.get("asset_market", "TH"))
        t = str(r["schedule_time"])[:5]  # HH:MM
        days = days_labels.get(r["schedule_days"], r["schedule_days"])
        lines.append(f"#{r['id']} {label} → {t} น. ({days})")

    lines.append("\nพิมพ์ 'ลบแจ้งเตือนเวลา [หมายเลข]' เพื่อลบ")
    msg.reply(reply_token, [msg.text_msg("\n".join(lines))])


def _cmd_delete_schedule(user_id: str, reply_token: str, parts: list[str]):
    if len(parts) < 2:
        msg.reply(reply_token, [msg.text_msg("ระบุหมายเลข เช่น: ลบแจ้งเตือนเวลา 2")])
        return
    try:
        sched_id = int(parts[1])
    except ValueError:
        msg.reply(reply_token, [msg.text_msg(f"หมายเลข '{parts[1]}' ไม่ถูกต้อง")])
        return

    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE scheduled_alerts SET is_active = 0 WHERE id = %s AND user_id = %s AND is_active = 1",
        (sched_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if affected:
        msg.reply(reply_token, [msg.text_msg(f"🗑️ ลบแจ้งเตือนเวลา #{sched_id} แล้ว")])
    else:
        msg.reply(reply_token, [msg.text_msg(f"ไม่พบแจ้งเตือนเวลา #{sched_id}")])


# ── Help ─────────────────────────────────────────────────────────────────────────

_HELP_QR = [
    ("💰 ราคาทอง",       "ราคา ทอง"),
    ("📈 ดูแจ้งเตือน",   "ดูแจ้งเตือน"),
    ("🕐 ดูตารางเวลา",   "ดูแจ้งเตือนเวลา"),
    ("🗑 ลบทั้งหมด",     "ลบแจ้งเตือนทั้งหมด"),
]


def _cmd_help(reply_token: str):
    msg.reply(reply_token, [msg.text_msg(
        "💡 คำสั่งทั้งหมด\n\n"
        "📈 ดูราคา:\n"
        "• ราคา ทอง  (หรือ: โกลด์, xau)\n"
        "• ราคา หุ้น PTT  (หรือ: set, ตลาดหุ้น)\n"
        "• ราคา หุ้นเมกา AAPL  (หรือ: เมกา, นาสแด็ก)\n"
        "• ราคา คริปโต BTC  (หรือ: คอยน์, เหรียญ)\n\n"
        "🔔 แจ้งเตือนราคา:\n"
        "• แจ้งเตือน ทอง 45000\n"
        "• แจ้งเตือน ทอง สูงกว่า 46000\n"
        "• แจ้งเตือน หุ้น PTT ต่ำกว่า 35\n"
        "• แจ้งเตือน หุ้นเมกา AAPL 200\n"
        "• แจ้งเตือน คริปโต BTC 3500000\n\n"
        "🕐 แจ้งเตือนตามเวลา:\n"
        "• แจ้งเตือนเวลา ทอง 09:00\n"
        "• แจ้งเตือนเวลา ทอง 09:00 วันธรรมดา\n"
        "• แจ้งเตือนเวลา หุ้น PTT 09:30\n"
        "• แจ้งเตือนเวลา หุ้นเมกา TSLA 16:00 วันหยุด\n"
        "• แจ้งเตือนเวลา คริปโต BTC 08:00\n\n"
        "📋 จัดการ:\n"
        "• ดูแจ้งเตือน\n"
        "• ดูแจ้งเตือนเวลา\n"
        "• ลบแจ้งเตือน [หมายเลข]\n"
        "• ลบแจ้งเตือนเวลา [หมายเลข]\n"
        "• ลบแจ้งเตือนทั้งหมด\n\n"
        f"💰 คริปโตที่รองรับ:\n{', '.join(CRYPTO_SUPPORTED)}",
        _HELP_QR,
    )])


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _get_current_price(asset_type: str, symbol: str | None, market: str = "TH") -> float | None:
    if asset_type == "gold":
        data = gold.fetch()
        return data.bar_buy if data else None
    if asset_type == "stock":
        data = stock.fetch(symbol, market)
        return data.price if data else None
    if asset_type == "crypto":
        data = crypto.fetch(symbol)
        return data.price_thb if data else None
    return None


def _asset_label(asset_type: str, symbol: str | None, market: str = "TH") -> str:
    if asset_type == "gold":
        return "ทองคำ (แท่งซื้อ)"
    if asset_type == "stock":
        mkt = " (US)" if market == "US" else " (SET)"
        return f"หุ้น {symbol}{mkt}"
    if asset_type == "crypto":
        return f"คริปโต {symbol}"
    return asset_type


def _parse_time(s: str) -> str | None:
    m = re.match(r'^(\d{1,2})[:.：](\d{2})$', s.strip())
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}:00"
    return None
