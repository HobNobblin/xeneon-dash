import asyncio
import time

import yfinance as yf
from fastapi import APIRouter, HTTPException

router = APIRouter()

_quote_cache: dict[str, dict] = {}
_history_cache: dict[str, dict] = {}
_QUOTE_TTL   = 60    # seconds
_HISTORY_TTL = 300   # 5 minutes


def _fetch_quote(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).fast_info
        price = info.last_price
        prev  = info.previous_close
        if price is None or prev is None:
            return {"symbol": symbol, "error": "no data"}
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0
        return {
            "symbol":     symbol,
            "price":      round(price, 2),
            "change":     round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def _fetch_history(symbol: str) -> list:
    try:
        hist = yf.Ticker(symbol).history(period="1d", interval="5m")
        if hist.empty:
            # fall back to last available day
            hist = yf.Ticker(symbol).history(period="5d", interval="5m").tail(78)
        result = []
        for ts, row in hist.iterrows():
            result.append({
                "time":  ts.strftime("%H:%M"),
                "open":  round(row["Open"],  2),
                "high":  round(row["High"],  2),
                "low":   round(row["Low"],   2),
                "close": round(row["Close"], 2),
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


@router.get("/quotes")
async def get_quotes(symbols: str):
    if not symbols.strip():
        raise HTTPException(status_code=400, detail="symbols parameter is required")

    now = time.time()
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    result, to_fetch = [], []

    for sym in symbol_list:
        cached = _quote_cache.get(sym)
        if cached and now - cached["_ts"] < _QUOTE_TTL:
            result.append({k: v for k, v in cached.items() if k != "_ts"})
        else:
            to_fetch.append(sym)

    if to_fetch:
        loop = asyncio.get_event_loop()
        fetched = await asyncio.gather(
            *[loop.run_in_executor(None, _fetch_quote, sym) for sym in to_fetch]
        )
        for sym, data in zip(to_fetch, fetched):
            _quote_cache[sym] = {**data, "_ts": now}
            result.append(data)

    order = {s: i for i, s in enumerate(symbol_list)}
    result.sort(key=lambda d: order.get(d["symbol"], 999))
    return result


@router.get("/history")
async def get_history(symbol: str):
    sym = symbol.strip().upper()
    now = time.time()
    cached = _history_cache.get(sym)
    if cached and now - cached["_ts"] < _HISTORY_TTL:
        return cached["data"]

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_history, sym)
    _history_cache[sym] = {"data": data, "_ts": now}
    return data
