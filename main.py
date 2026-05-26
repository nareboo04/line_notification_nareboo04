import time
import datetime
from app import database as db
from app.config import ALERT_CHECK_INTERVAL, DAILY_REPORT_HOUR
from app.services.alert_checker import (
    check_price_alerts,
    check_scheduled_alerts,
    send_daily_gold_report,
)


def get_all_user_ids() -> list[str]:
    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [r[0] for r in rows]


def main():
    print("[main] initializing database...")
    db.init_db()
    print(f"[main] schedule check: every 60s | price check: every {ALERT_CHECK_INTERVAL}s | daily report: {DAILY_REPORT_HOUR}:00")

    last_price_check  = 0.0
    last_daily_date: datetime.date | None = None

    while True:
        now = datetime.datetime.now()

        # ── Schedule alerts: check every minute ──────────────────────────────
        try:
            check_scheduled_alerts()
        except Exception as e:
            print(f"[main] schedule check error: {e}")

        # ── Price alerts: check every ALERT_CHECK_INTERVAL ───────────────────
        if time.monotonic() - last_price_check >= ALERT_CHECK_INTERVAL:
            try:
                print(f"[main] checking price alerts at {now.strftime('%H:%M:%S')}")
                check_price_alerts()
            except Exception as e:
                print(f"[main] price check error: {e}")
            last_price_check = time.monotonic()

        # ── Daily gold report ────────────────────────────────────────────────
        if now.hour == DAILY_REPORT_HOUR and now.minute == 0:
            if last_daily_date != now.date():
                print("[main] sending daily gold report")
                try:
                    send_daily_gold_report(get_all_user_ids())
                except Exception as e:
                    print(f"[main] daily report error: {e}")
                last_daily_date = now.date()

        time.sleep(60)


if __name__ == "__main__":
    main()
