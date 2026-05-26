# Gold Alert — LINE Bot

แจ้งเตือนราคา ทองคำ / หุ้นไทย / หุ้น US / คริปโต ผ่าน LINE Messaging API

## Features

- ดูราคาทองคำ หุ้น SET / US และคริปโตแบบ Real-time
- ตั้งแจ้งเตือนเมื่อราคาถึงเป้าหมาย (สูงกว่า / ต่ำกว่า)
- ตั้งแจ้งเตือนตามเวลา (ทุกวัน / วันธรรมดา / วันหยุด)
- ส่งรายงานราคาทองประจำวัน
- ควบคุมทุกอย่างผ่านแชท LINE

## Getting Started

### 1. ตั้งค่า .env

```bash
cp .env.example .env
```

แก้ค่าใน `.env`:

| ตัวแปร | คำอธิบาย |
|--------|-----------|
| `LINE_TOKEN` | Channel Access Token จาก LINE Developers Console |
| `MYSQL_ROOT_PASSWORD` | รหัสผ่าน MySQL (ตั้งให้แข็งแรง) |
| `MYSQL_DATABASE` | ชื่อฐานข้อมูล (default: `users_db`) |
| `ALERT_CHECK_INTERVAL` | ตรวจราคาทุกกี่วินาที (default: `300`) |
| `DAILY_REPORT_HOUR` | ส่งรายงานทองกี่โมง 24h Bangkok (default: `18`) |
| `API_PORT` | Port สำหรับ webhook (default: `5000`) |

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

### 4. ดู logs

```bash
docker compose logs -f api     # webhook server
docker compose logs -f main    # scheduler / alert checker
```

## Project Structure

```
Gold-Alert/
├── app/
│   ├── api.py          # FastAPI webhook server
│   ├── main.py         # Scheduler loop
│   ├── config.py       # Environment config
│   ├── database.py     # MySQL connection
│   ├── line/
│   │   ├── commands.py     # Command parser
│   │   └── messaging.py    # LINE message builders
│   ├── scrapers/
│   │   ├── gold.py         # ราคาทองคำ
│   │   ├── stock.py        # หุ้น SET / US (yfinance)
│   │   └── crypto.py       # คริปโต (CoinGecko)
│   └── services/
│       └── alert_checker.py  # Price & schedule alert logic
├── Dockerfile
├── docker-compose.yml
├── database.sql
└── .env.example
```

## คำสั่ง LINE

| คำสั่ง | ตัวอย่าง |
|--------|---------|
| ดูราคา | `ราคา ทอง` / `ราคา หุ้น PTT` / `ราคา หุ้นเมกา AAPL` / `ราคา คริปโต BTC` |
| แจ้งเตือนราคา | `แจ้งเตือน ทอง 45000` / `แจ้งเตือน หุ้นเมกา AAPL สูงกว่า 200` |
| แจ้งเตือนเวลา | `แจ้งเตือนเวลา ทอง 09:00 วันธรรมดา` |
| ดูรายการ | `ดูแจ้งเตือน` / `ดูแจ้งเตือนเวลา` |
| ลบ | `ลบแจ้งเตือน 1` / `ลบแจ้งเตือนทั้งหมด` |
| ช่วยเหลือ | `ช่วยเหลือ` / `help` / `เมนู` |

## Data Sources

- ทองคำ: [ราคาทอง.com](https://ทองคำราคา.com/)
- หุ้น: [yfinance](https://github.com/ranaroussi/yfinance) (SET / NYSE / NASDAQ)
- คริปโต: [CoinGecko API](https://www.coingecko.com/) (ไม่ต้องใช้ API key)
