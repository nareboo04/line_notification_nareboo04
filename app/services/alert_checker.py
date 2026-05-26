"""
Alert checker service.

check_price_alerts()    → run every 5 minutes — fire when price crosses target
check_scheduled_alerts() → run every minute   — fire at the scheduled time
send_daily_gold_report() → run once at DAILY_REPORT_HOUR
"""

import datetime
from collections import defaultdict
from app import database as db
from app.line import messaging as msg
from app.scrapers import gold, stock, crypto


# ── Price alerts ─────────────────────────────────────────────────────────────────

def check_price_alerts():
    conn = db.get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, user_id, asset_type, asset_symbol, asset_market, target_price, condition_type "
        "FROM alerts WHERE is_active = 1"
    )
    alerts = cursor.fetchall()
    cursor.close()
    conn.close()

    if not alerts:
        return

    # Group by (asset_type, symbol, market) — fetch each price only once
    groups: dict[tuple, list] = defaultdict(list)
    for alert in alerts:
        key = (alert["asset_type"], alert["asset_symbol"], alert.get("asset_market", "TH"))
        groups[key].append(alert)

    triggered_ids: list[int] = []

    for (asset_type, symbol, market), group in groups.items():
        current = _fetch_price(asset_type, symbol, market)
        if current is None:
            continue

        for alert in group:
            target    = float(alert["target_price"])
            condition = alert["condition_type"]
            fired = (condition == "above" and current >= target) or \
                    (condition == "below" and current <= target)

            if fired:
                triggered_ids.append(alert["id"])
                _notify_price_alert(alert, current)

    if triggered_ids:
        conn = db.get_conn()
        cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(triggered_ids))
        cursor.execute(f"UPDATE alerts SET is_active = 0 WHERE id IN ({placeholders})", triggered_ids)
        conn.commit()
        cursor.close()
        conn.close()


# ── Schedule alerts ───────────────────────────────────────────────────────────────

def check_scheduled_alerts():
    now = datetime.datetime.now()
    today = now.date()
    weekday = now.weekday()  # 0=Mon … 6=Sun

    conn = db.get_conn()
    cursor = conn.cursor(dictionary=True)
    # Match alerts whose schedule_time falls in the current minute and haven't fired today
    cursor.execute(
        "SELECT * FROM scheduled_alerts "
        "WHERE is_active = 1 "
        "AND HOUR(schedule_time) = %s AND MINUTE(schedule_time) = %s "
        "AND (last_fired_date IS NULL OR last_fired_date < %s)",
        (now.hour, now.minute, today),
    )
    schedules = cursor.fetchall()
    cursor.close()
    conn.close()

    if not schedules:
        return

    fired_ids: list[int] = []

    for sched in schedules:
        if not _day_matches(sched["schedule_days"], weekday):
            continue

        asset_type = sched["asset_type"]
        symbol     = sched["asset_symbol"]
        market     = sched.get("asset_market", "TH")

        current = _fetch_price(asset_type, symbol, market)
        if current is None:
            print(f"[schedule] #{sched['id']} — price unavailable, skipping")
            continue

        _notify_scheduled(sched, current)
        fired_ids.append(sched["id"])

    if fired_ids:
        conn = db.get_conn()
        cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(fired_ids))
        cursor.execute(
            f"UPDATE scheduled_alerts SET last_fired_date = %s WHERE id IN ({placeholders})",
            [today] + fired_ids,
        )
        conn.commit()
        cursor.close()
        conn.close()


# ── Daily gold report ─────────────────────────────────────────────────────────────

def send_daily_gold_report(users: list[str]):
    data = gold.fetch()
    if not data:
        print("[daily report] failed to fetch gold price")
        return
    bubble = msg.build_gold_bubble(data)
    for user_id in users:
        msg.push(user_id, [msg.flex_msg("ราคาทองคำประจำวัน", bubble)])


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _fetch_price(asset_type: str, symbol: str | None, market: str = "TH") -> float | None:
    try:
        if asset_type == "gold":
            data = gold.fetch()
            return data.bar_buy if data else None
        if asset_type == "stock":
            data = stock.fetch(symbol, market)
            return data.price if data else None
        if asset_type == "crypto":
            data = crypto.fetch(symbol)
            return data.price_thb if data else None
    except Exception as e:
        print(f"[alert_checker] fetch error ({asset_type} {symbol} {market}): {e}")
    return None


def _day_matches(schedule_days: str, weekday: int) -> bool:
    if schedule_days == "daily":
        return True
    if schedule_days == "weekday":
        return weekday < 5   # Mon–Fri
    if schedule_days == "weekend":
        return weekday >= 5  # Sat–Sun
    return True


def _notify_price_alert(alert: dict, current_price: float):
    try:
        bubble = msg.build_alert_triggered_bubble(alert, current_price)
        asset_type = alert["asset_type"]
        symbol = alert.get("asset_symbol") or ""
        labels = {"gold": "ทองคำ", "stock": f"หุ้น {symbol}", "crypto": f"คริปโต {symbol}"}
        alt = f"🔔 {labels.get(asset_type, '')} ถึงราคาเป้าหมาย!"
        msg.push(alert["user_id"], [msg.flex_msg(alt, bubble)])
        print(f"[price alert] fired #{alert['id']} → {alert['user_id']}")
    except Exception as e:
        print(f"[price alert] notify error: {e}")


def _notify_scheduled(sched: dict, current_price: float):
    try:
        asset_type = sched["asset_type"]
        symbol     = sched.get("asset_symbol") or ""
        market     = sched.get("asset_market", "TH")
        time_str   = str(sched["schedule_time"])[:5]  # HH:MM

        asset_labels = {"gold": "ทองคำ", "stock": f"หุ้น {symbol}", "crypto": f"คริปโต {symbol}"}
        asset_label = asset_labels.get(asset_type, "")
        if asset_type == "stock" and market == "US":
            asset_label = f"หุ้น {symbol} (US)"

        # Build appropriate card
        if asset_type == "gold":
            data = gold.fetch()
            bubble = msg.build_gold_bubble(data) if data else None
        elif asset_type == "stock":
            data = stock.fetch(symbol, market)
            bubble = msg.build_stock_bubble(data) if data else None
        elif asset_type == "crypto":
            data = crypto.fetch(symbol)
            bubble = msg.build_crypto_bubble(data) if data else None
        else:
            bubble = None

        if bubble:
            alt = f"📊 อัพเดทราคา {asset_label} เวลา {time_str}"
            msg.push(sched["user_id"], [msg.flex_msg(alt, bubble)])
        else:
            msg.push(sched["user_id"], [msg.text_msg(
                f"📊 {asset_label} เวลา {time_str}\nราคา: {current_price:,.2f}"
            )])

        print(f"[schedule] fired #{sched['id']} → {sched['user_id']}")
    except Exception as e:
        print(f"[schedule] notify error: {e}")
