# Gold Alert — LINE Bot

แจ้งเตือนราคา ทองคำ / หุ้นไทย / หุ้น US / คริปโต ผ่าน LINE Messaging API

## Features

- ดูราคาทองคำ หุ้น SET / US และคริปโตแบบ Real-time
- ตั้งแจ้งเตือนเมื่อราคาถึงเป้าหมาย (สูงกว่า / ต่ำกว่า) — ตรวจทุก 5 นาที
- ตั้งแจ้งเตือนตามเวลา (ทุกวัน / วันธรรมดา / วันหยุด)
- ส่งรายงานราคาทองประจำวันอัตโนมัติ
- Rich Menu — เมนูถาวรด้านล่างแชท กดได้เลยไม่ต้องพิมพ์
- ตรวจสอบ LINE Signature ทุก request (ป้องกัน request ปลอม)
- ควบคุมทุกอย่างผ่านแชท LINE

## Getting Started

### 1. ตั้งค่า .env

```bash
cp .env.example .env
```

แก้ค่าใน `.env`:

| ตัวแปร | คำอธิบาย | หาได้จาก |
|--------|-----------|----------|
| `LINE_TOKEN` | Channel Access Token | LINE Developers → Messaging API |
| `LINE_CHANNEL_SECRET` | Channel Secret | LINE Developers → Basic settings |
| `MYSQL_ROOT_PASSWORD` | รหัสผ่าน MySQL (ตั้งให้แข็งแรง) | กำหนดเอง |
| `MYSQL_DATABASE` | ชื่อฐานข้อมูล (default: `users_db`) | — |
| `ALERT_CHECK_INTERVAL` | ตรวจราคาทุกกี่วินาที (default: `300`) | — |
| `DAILY_REPORT_HOUR` | ส่งรายงานทองกี่โมง 24h Bangkok (default: `18`) | — |
| `MAX_PRICE_ALERTS` | แจ้งเตือนราคาสูงสุดต่อ user (default: `10`) | — |
| `MAX_SCHED_ALERTS` | แจ้งเตือนเวลาสูงสุดต่อ user (default: `10`) | — |
| `API_PORT` | Port สำหรับ webhook (default: `5000`) | — |

### 2. ตั้งค่า LINE Webhook

ใน [LINE Developers Console](https://developers.line.biz/) → Messaging API → Webhook URL:

```
https://your-domain.com/webhook
```

### 3. รัน Docker

```bash
# Production
docker compose up --build -d

# Development (เปิด phpMyAdmin ที่ port 8080 ด้วย)
docker compose --profile dev up --build -d
```

### 4. ตั้ง Rich Menu (ครั้งเดียว)

```bash
pip install Pillow
python setup_richmenu.py
```

เมนูจะขึ้นถาวรด้านล่างแชทสำหรับทุก user:

```
┌──────────┬──────────┬──────────┐
│ ราคาทอง │ หุ้นไทย  │ หุ้นเมกา │
├──────────┼──────────┼──────────┤
│ คริปโต  │ แจ้งเตือน│ ช่วยเหลือ│
└──────────┴──────────┴──────────┘
```

### 5. ดู logs

```bash
docker compose logs -f api     # webhook server
docker compose logs -f main    # scheduler / alert checker
```

## คำสั่ง LINE

รองรับหลายคำพ้องความหมาย เช่น `ราคา` / `เช็คราคา` / `ดูราคา` / `เช็ค`

| หมวด | ตัวอย่างคำสั่ง |
|------|--------------|
| **ดูราคา** | `ราคา ทอง` · `เช็ค หุ้น PTT` · `ราคา หุ้นเมกา AAPL` · `ราคา คริปโต BTC` |
| **คำพ้อง สินทรัพย์** | ทอง: `โกลด์` `xau` · หุ้น US: `หุ้นเมกา` `เมกา` `nasdaq` · คริปโต: `คอยน์` `เหรียญ` |
| **แจ้งเตือนราคา** | `แจ้งเตือน ทอง 45000` · `แจ้งเตือน ทอง สูงกว่า 46000` · `แจ้งเตือน หุ้นเมกา AAPL 200` |
| **แจ้งเตือนเวลา** | `แจ้งเตือนเวลา ทอง 09:00` · `แจ้งเตือนเวลา หุ้น PTT 09:30 วันธรรมดา` |
| **ดูรายการ** | `ดูแจ้งเตือน` (แสดงทั้งราคาและเวลาในคำสั่งเดียว) |
| **ลบ** | `ลบแจ้งเตือน 1` · `ลบแจ้งเตือนเวลา 2` · `ลบแจ้งเตือนทั้งหมด` |
| **ช่วยเหลือ** | `ช่วยเหลือ` · `help` · `เมนู` · `?` |

## Project Structure

```
Gold-Alert/
├── app/
│   ├── api.py              # FastAPI webhook + LINE signature verification
│   ├── main.py             # Scheduler loop
│   ├── config.py           # Environment config
│   ├── database.py         # MySQL connection (retry 10x)
│   ├── line/
│   │   ├── commands.py     # Command parser + keyword sets
│   │   └── messaging.py    # LINE Flex Message builders
│   ├── scrapers/
│   │   ├── gold.py         # ราคาทองคำ (scrape)
│   │   ├── stock.py        # หุ้น SET / US (yfinance)
│   │   └── crypto.py       # คริปโต (CoinGecko free API)
│   └── services/
│       └── alert_checker.py  # Price & schedule alert logic
├── setup_richmenu.py       # One-time Rich Menu setup script
├── Dockerfile
├── docker-compose.yml
├── database.sql
└── .env.example
```

## Data Sources

- ทองคำ: scrape จาก [ราคาทอง.com](https://ทองคำราคา.com/)
- หุ้น: [yfinance](https://github.com/ranaroussi/yfinance) (SET `.BK` / NYSE / NASDAQ)
- คริปโต: [CoinGecko API](https://www.coingecko.com/) — ฟรี ไม่ต้อง API key
