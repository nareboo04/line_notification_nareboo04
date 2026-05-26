import json
import requests
from app.config import LINE_TOKEN
from app.scrapers.gold import GoldPrice
from app.scrapers.stock import StockPrice
from app.scrapers.crypto import CryptoPrice

_PUSH_URL  = "https://api.line.me/v2/bot/message/push"
_REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def _headers() -> dict:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}


def push(user_id: str, messages: list[dict]):
    payload = {"to": user_id, "messages": messages}
    try:
        r = requests.post(_PUSH_URL, headers=_headers(), data=json.dumps(payload), timeout=10)
        if r.status_code != 200:
            print(f"[push] {r.status_code} {r.text}")
    except Exception as e:
        print(f"[push] error: {e}")


def reply(reply_token: str, messages: list[dict]):
    payload = {"replyToken": reply_token, "messages": messages}
    try:
        r = requests.post(_REPLY_URL, headers=_headers(), data=json.dumps(payload), timeout=10)
        if r.status_code != 200:
            print(f"[reply] {r.status_code} {r.text}")
    except Exception as e:
        print(f"[reply] error: {e}")


def text_msg(content: str, qr: list[tuple[str, str]] | None = None) -> dict:
    m: dict = {"type": "text", "text": content}
    if qr:
        m["quickReply"] = {
            "items": [
                {"type": "action", "action": {"type": "message", "label": lbl, "text": txt}}
                for lbl, txt in qr
            ]
        }
    return m


def flex_msg(alt_text: str, bubble: dict) -> dict:
    return {"type": "flex", "altText": alt_text, "contents": bubble}


# ── Flex bubble builders ────────────────────────────────────────────────────────

def _row(label: str, value: str, value_color: str = "#333333") -> dict:
    return {
        "type": "box", "layout": "baseline", "spacing": "sm",
        "contents": [
            {"type": "text", "text": label, "flex": 5, "size": "sm", "color": "#aaaaaa"},
            {"type": "text", "text": value,  "flex": 4, "size": "sm", "align": "end",
             "weight": "bold", "color": value_color, "wrap": True},
        ],
    }


def build_gold_bubble(data: GoldPrice) -> dict:
    status_map = {"up": ("ขึ้น ↑", "#2ecc71"), "down": ("ลง ↓", "#e74c3c"), "flat": ("ทรงตัว", "#95a5a6")}
    status_text, color = status_map.get(data.change_status, ("", "#666666"))

    return {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": "https://cdn.pixabay.com/photo/2014/11/01/22/33/gold-513062_1280.jpg",
            "size": "full", "aspectRatio": "20:9", "aspectMode": "cover",
        },
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": "#B8860B",
            "contents": [
                {"type": "text", "text": "ราคาทองคำ", "color": "#ffffff", "weight": "bold", "size": "xl"},
                {"type": "text", "text": f"{data.updated_date} {data.updated_time}",
                 "color": "#ffffffaa", "size": "xs"},
            ],
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                _row("ทองแท่ง ซื้อ",      f"{data.bar_buy:,.2f} ฿"),
                _row("ทองแท่ง ขาย",      f"{data.bar_sell:,.2f} ฿"),
                {"type": "separator", "margin": "sm"},
                _row("ทองรูปพรรณ ซื้อ",  f"{data.ornament_buy:,.2f} ฿"),
                _row("ทองรูปพรรณ ขาย",  f"{data.ornament_sell:,.2f} ฿"),
                {"type": "separator", "margin": "sm"},
                _row("เปลี่ยนแปลง", f"{data.change_amount} {status_text}", color),
            ],
        },
    }


def build_stock_bubble(data: StockPrice) -> dict:
    change_color = "#2ecc71" if data.change >= 0 else "#e74c3c"
    sign = "+" if data.change >= 0 else ""
    sym = "$" if data.currency == "USD" else "฿"
    market_label = "ราคาหุ้น US" if data.market == "US" else "ราคาหุ้น SET"

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": "#1a73e8",
            "contents": [
                {"type": "text", "text": market_label, "color": "#ffffff", "size": "sm"},
                {"type": "text", "text": data.symbol, "color": "#ffffff", "weight": "bold", "size": "xxl"},
                {"type": "text", "text": data.name, "color": "#ffffffbb", "size": "xs", "wrap": True},
            ],
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                {
                    "type": "text", "text": f"{sym}{data.price:,.2f}" if sym == "$" else f"{data.price:,.2f} {sym}",
                    "size": "xxl", "weight": "bold", "align": "center", "color": "#1a73e8",
                },
                _row("ราคาปิดเมื่อวาน", f"{sym}{data.prev_close:,.2f}" if sym == "$" else f"{data.prev_close:,.2f} {sym}"),
                _row("เปลี่ยนแปลง",
                     f"{sign}{data.change:,.2f} ({sign}{data.change_pct:.2f}%)", change_color),
            ],
        },
    }


def build_crypto_bubble(data: CryptoPrice) -> dict:
    change_color = "#2ecc71" if data.change_24h >= 0 else "#e74c3c"
    sign = "+" if data.change_24h >= 0 else ""
    header_colors = {
        "BTC": "#f7931a", "ETH": "#627eea", "BNB": "#f3ba2f",
        "SOL": "#9945ff", "XRP": "#346aa9",
    }
    bg = header_colors.get(data.symbol, "#333333")

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": bg,
            "contents": [
                {"type": "text", "text": "ราคาคริปโต", "color": "#ffffff", "size": "sm"},
                {"type": "text", "text": data.symbol, "color": "#ffffff", "weight": "bold", "size": "xxl"},
            ],
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                _row("ราคา (THB)", f"{data.price_thb:,.2f} ฿"),
                _row("ราคา (USD)", f"${data.price_usd:,.2f}"),
                {"type": "separator", "margin": "sm"},
                _row("เปลี่ยนแปลง 24ชม.", f"{sign}{data.change_24h:.2f}%", change_color),
            ],
        },
    }


def build_alert_triggered_bubble(alert: dict, current_price: float) -> dict:
    asset_labels = {"gold": "ทองคำ", "stock": "หุ้น", "crypto": "คริปโต"}
    asset_label = asset_labels.get(alert["asset_type"], "")
    symbol = alert.get("asset_symbol") or ""
    title = f"{asset_label} {symbol}".strip()
    cond_text = "สูงกว่า" if alert["condition_type"] == "above" else "ต่ำกว่า"
    target = float(alert["target_price"])

    is_usd = alert.get("asset_type") == "stock" and alert.get("asset_market") == "US"
    sym = "$" if is_usd else "฿"
    _fmt = lambda v: f"${v:,.2f}" if is_usd else f"{v:,.2f} ฿"

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": "#e74c3c",
            "contents": [
                {"type": "text", "text": "🔔 แจ้งเตือนราคา!", "color": "#ffffff", "weight": "bold", "size": "xl"},
                {"type": "text", "text": "ราคาถึงเป้าหมายแล้ว", "color": "#ffffffaa", "size": "sm"},
            ],
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                _row("สินทรัพย์", title),
                _row("เงื่อนไข", f"{cond_text} {_fmt(target)}"),
                {"type": "separator", "margin": "sm"},
                _row("ราคาปัจจุบัน", _fmt(current_price), "#e74c3c"),
            ],
        },
    }
