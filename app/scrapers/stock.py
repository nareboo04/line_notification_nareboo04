import yfinance as yf
from dataclasses import dataclass
from typing import Optional


@dataclass
class StockPrice:
    symbol: str
    name: str
    price: float
    prev_close: float
    change: float
    change_pct: float
    currency: str
    market: str  # 'TH' | 'US'


def fetch(symbol: str, market: str = "TH") -> Optional[StockPrice]:
    try:
        ticker_sym = symbol.upper()
        if market == "TH" and not ticker_sym.endswith(".BK"):
            ticker_sym += ".BK"
        # market == "US": use symbol as-is (e.g. AAPL, TSLA)

        ticker = yf.Ticker(ticker_sym)
        info = ticker.fast_info

        price = info.last_price
        if price is None:
            return None

        prev_close = getattr(info, "previous_close", price) or price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        full_info = ticker.info
        name = full_info.get("shortName") or full_info.get("longName") or symbol.upper()
        currency = full_info.get("currency", "USD" if market == "US" else "THB")

        return StockPrice(
            symbol=symbol.upper(),
            name=name,
            price=round(float(price), 2),
            prev_close=round(float(prev_close), 2),
            change=round(float(change), 2),
            change_pct=round(float(change_pct), 2),
            currency=currency,
            market=market,
        )
    except Exception as e:
        print(f"[stock] {symbol} ({market}) error: {e}")
        return None
