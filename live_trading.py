import asyncio
import os
import sys
from datetime import datetime, time
from threading import Event as ThreadEvent

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from indicators.bollinger_bands import BollingerBands

from paperbroker.client import PaperBrokerClient
from paperbroker.market_data import RedisMarketDataClient

# ── Config ────────────────────────────────────────────────────────────────────
REDIS_SYMBOL  = "HNXDS:VN30F2605"   # May 2026 near-month contract
FIX_SYMBOL    = "VN30F2605"          # no exchange prefix for FIX orders
BB_WINDOW     = 20
BB_STD        = 1.8
TF_MINUTES    = 15
STOP_LOSS_PTS = 2.0
MAX_TRADES    = 30                   # stop after 30 total trades
TRADING_START = time(9, 15)
ENTRY_CUTOFF  = time(14, 0)
FORCE_CLOSE   = time(14, 30)

bb = BollingerBands(window=BB_WINDOW, num_std=BB_STD)
_fix_ready = ThreadEvent()

# ── State ─────────────────────────────────────────────────────────────────────
candles        = []
current_candle = None
position       = None   # None or dict with buy/sell order IDs and entry_price
trades_done    = 0

# ── FIX Client ────────────────────────────────────────────────────────────────
fix = PaperBrokerClient(
    default_sub_account="D1",
    username="Group07",
    password="U13tC8z6H8tO",
    rest_base_url="https://papertrade.algotrade.vn/accounting",
    socket_connect_host="papertrade.algotrade.vn",
    socket_connect_port=5001,
    sender_comp_id="cf030e89c06043adbcd53a5b240a8910",
    target_comp_id="SERVER",
    console=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def candle_slot(ts: datetime) -> datetime:
    m = (ts.minute // TF_MINUTES) * TF_MINUTES
    return ts.replace(minute=m, second=0, microsecond=0)

def compute_signal():
    """Returns (buy_signal: bool, sma: float|None) on the last completed candle."""
    if len(candles) < BB_WINDOW + 1:
        return False, None
    df = pd.DataFrame(candles[-(BB_WINDOW + 5):])
    df = bb.calculate(df)
    if df["lower_band"].isna().iloc[-1]:
        return False, None
    prev, curr = df.iloc[-2], df.iloc[-1]
    signal = (prev["close"] > prev["lower_band"]) and (curr["close"] <= curr["lower_band"])
    return signal, float(df["sma"].iloc[-1])

def place_buy(price: float):
    global position
    cl_ord_id = fix.place_order(
        symbol=FIX_SYMBOL, side="BUY", quantity=1,
        price=round(price, 1), order_type="LIMIT",
    )
    position = {"buy_id": cl_ord_id, "entry_price": None, "sell_id": None}
    log(f"BUY order → {price:.1f}  (total filled so far: {trades_done})")

def place_sell(price: float, reason: str):
    global position
    if position is None or position.get("sell_id"):
        return
    cl_ord_id = fix.place_order(
        symbol=FIX_SYMBOL, side="SELL", quantity=1,
        price=round(price, 1), order_type="LIMIT",
    )
    position["sell_id"] = cl_ord_id
    log(f"SELL order → {price:.1f}  [{reason}]")

# ── FIX Event Handlers ────────────────────────────────────────────────────────

def on_logon(session_id, **kw):
    log(f"FIX connected: {session_id}")
    _fix_ready.set()

def on_fill(cl_ord_id, last_px, last_qty, **kw):
    global position, trades_done
    if position is None:
        return
    if position.get("buy_id") == cl_ord_id and position["entry_price"] is None:
        position["entry_price"] = last_px
        trades_done += 1
        log(f"BUY filled @ {last_px}  [{trades_done}/{MAX_TRADES} trades]")
    elif position.get("sell_id") == cl_ord_id:
        entry = position.get("entry_price") or last_px
        log(f"SELL filled @ {last_px}  pnl={last_px - entry:+.1f} pts")
        position = None

def on_rejected(cl_ord_id, reason=None, **kw):
    log(f"Order REJECTED cl_ord_id={cl_ord_id} reason={reason}")

fix.on("fix:logon", on_logon)
fix.on("fix:order:filled", on_fill)
fix.on("fix:order:rejected", on_rejected)

# ── Market Data Handler ───────────────────────────────────────────────────────

def on_quote(instrument, quote):
    global current_candle, candles, position

    px = quote.latest_matched_price
    if not px:
        return

    now  = datetime.now()
    t    = now.time()
    slot = candle_slot(now)

    # Force close all positions at 14:45
    if t >= FORCE_CLOSE:
        if position and position["entry_price"] and not position["sell_id"]:
            place_sell(px, "time_close")
        return

    # Build 15-min candle
    if current_candle is None:
        current_candle = {"datetime": slot, "open": px, "high": px, "low": px, "close": px}
    elif slot > current_candle["datetime"]:
        # Candle just closed
        candles.append(current_candle)
        current_candle = {"datetime": slot, "open": px, "high": px, "low": px, "close": px}

        # Check take-profit on candle close
        if position and position["entry_price"] and not position["sell_id"]:
            _, sma = compute_signal()
            if sma and px >= sma:
                place_sell(px, "take_profit")

        # Check entry signal
        elif (position is None
              and trades_done < MAX_TRADES
              and TRADING_START <= t < ENTRY_CUTOFF):
            signal, _ = compute_signal()
            if signal:
                place_buy(px)
    else:
        current_candle["high"]  = max(current_candle["high"], px)
        current_candle["low"]   = min(current_candle["low"],  px)
        current_candle["close"] = px

    # Intra-candle stop-loss check
    if position and position["entry_price"] and not position["sell_id"]:
        if px <= position["entry_price"] - STOP_LOSS_PTS:
            place_sell(px, "stop_loss")

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    fix.connect()
    if not _fix_ready.wait(timeout=6000):
        log("FIX login timed out — check credentials")
        os._exit(1)

    redis = RedisMarketDataClient(
        host="52.76.242.46",
        port=6380,
        password="Vn9ZMBF5SLafGkqEWc4h3b",
        merge_updates=True,
    )

    log(f"Subscribing to {REDIS_SYMBOL} ...")
    await redis.subscribe(REDIS_SYMBOL, on_quote)
    log("Live — Ctrl+C to stop")

    try:
        while True:
            await asyncio.sleep(1)
            if trades_done >= MAX_TRADES:
                log(f"Reached {MAX_TRADES} trades. Done!")
                break
            if datetime.now().time() >= time(15, 10):
                log(f"Market closed. Trades today: {trades_done}")
                break
    except KeyboardInterrupt:
        log("Stopped")
    finally:
        fix.disconnect()
        os._exit(0)  # avoid QuickFIX segfault on exit

if __name__ == "__main__":
    asyncio.run(main())
