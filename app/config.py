import os
from dotenv import load_dotenv

load_dotenv()

LINE_TOKEN: str = os.getenv('LINE_TOKEN', os.getenv('AUTHORIZATION', ''))

DB_CONFIG: dict = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'users_db'),
    'charset': 'utf8mb4',
}

ALERT_CHECK_INTERVAL: int = int(os.getenv('ALERT_CHECK_INTERVAL', 300))  # seconds
DAILY_REPORT_HOUR: int = int(os.getenv('DAILY_REPORT_HOUR', 18))         # 18 = 6 PM
