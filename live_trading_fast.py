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

# ── Config (optimized for fast trades) ───────────────────────────────────────
REDIS_SYMBOL  = "HNXDS:VN30F2605"
FIX_SYMBOL    = "VN30F2605"
BB_WINDOW     = 5      # only 5 candles needed → signals start in ~5 min
BB_STD        = 1.5    # tighter bands → more crossover signals
TF_MINUTES    = 1      # 1-min candles instead of 15-min
STOP_LOSS_PTS = 2.0
MAX_TRADES    = 10
TRADING_START = time(9, 0)
ENTRY_CUTOFF  = time(14, 25)
FORCE_CLOSE   = time(14, 29)

bb = BollingerBands(window=BB_WINDOW, num_std=BB_STD)
_fix_ready = ThreadEvent()

# ── State ─────────────────────────────────────────────────────────────────────
candles        = []
current_candle = None
position       = None
trades_done    = 0
last_quote     = None  # keep latest quote for bid/ask access

# ── FIX Client ────────────────────────────────────────────────────────────────
fix = PaperBrokerClient(
    default_sub_account="main",
    username="Group07",
    password="U13tC8z6H8tO",
    rest_base_url="https://papertrade.algotrade.vn/accounting",
    socket_connect_host="papertrade.algotrade.vn",
    socket_connect_port=5001,
    sender_comp_id="cf030e89c06043adbcd53a5b240a8910",
    target_comp_id="SERVER",
    console=False,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def candle_slot(ts: datetime) -> datetime:
    m = (ts.minute // TF_MINUTES) * TF_MINUTES
    return ts.replace(minute=m, second=0, microsecond=0)

def compute_signal():
    if len(candles) < BB_WINDOW + 1:
        return False, None
    df = pd.DataFrame(candles[-(BB_WINDOW + 5):])
    df = bb.calculate(df)
    if df["lower_band"].isna().iloc[-1]:
        return False, None
    prev, curr = df.iloc[-2], df.iloc[-1]
    signal = (prev["close"] > prev["lower_band"]) and (curr["close"] <= curr["lower_band"])
    return signal, float(df["sma"].iloc[-1])

def best_buy_price(quote):
    return quote.ask_price_1 or quote.latest_matched_price

def best_sell_price(quote):
    return quote.bid_price_1 or quote.latest_matched_price

def place_buy(quote):
    global position
    price = round(best_buy_price(quote), 1)
    cl_ord_id = fix.place_order(
        symbol=FIX_SYMBOL, side="BUY", quantity=1,
        price=price, order_type="LIMIT",
    )
    position = {"buy_id": cl_ord_id, "entry_price": None, "sell_id": None}
    log(f"BUY order → {price}  [{trades_done+1}/{MAX_TRADES}]")

def place_sell(quote, reason: str):
    global position
    if position is None or position.get("sell_id"):
        return
    price = round(best_sell_price(quote), 1)
    cl_ord_id = fix.place_order(
        symbol=FIX_SYMBOL, side="SELL", quantity=1,
        price=price, order_type="LIMIT",
    )
    position["sell_id"] = cl_ord_id
    log(f"SELL order → {price}  [{reason}]")

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
    global position
    log(f"Order REJECTED: {reason}")
    if position and position.get("buy_id") == cl_ord_id:
        position = None  # reset so we can try again

fix.on("fix:logon", on_logon)
fix.on("fix:order:filled", on_fill)
fix.on("fix:order:rejected", on_rejected)

# ── Market Data Handler ───────────────────────────────────────────────────────

def on_quote(instrument, quote):
    global current_candle, candles, position, last_quote

    px = quote.latest_matched_price
    if not px:
        return

    last_quote = quote
    now  = datetime.now()
    t    = now.time()
    slot = candle_slot(now)

    # Force close at 14:29
    if t >= FORCE_CLOSE:
        if position and position["entry_price"] and not position["sell_id"]:
            place_sell(quote, "time_close")
        return

    # Build 1-min candle
    if current_candle is None:
        current_candle = {"datetime": slot, "open": px, "high": px, "low": px, "close": px}
    elif slot > current_candle["datetime"]:
        candles.append(current_candle)
        current_candle = {"datetime": slot, "open": px, "high": px, "low": px, "close": px}
        log(f"Candle #{len(candles)}  close={candles[-1]['close']}  trades={trades_done}/{MAX_TRADES}")

        # Take-profit: price reached SMA
        if position and position["entry_price"] and not position["sell_id"]:
            _, sma = compute_signal()
            if sma and px >= sma:
                place_sell(quote, "take_profit")

        # Entry signal
        elif (position is None
              and trades_done < MAX_TRADES
              and TRADING_START <= t < ENTRY_CUTOFF):
            signal, _ = compute_signal()
            if signal:
                place_buy(quote)
    else:
        current_candle["high"]  = max(current_candle["high"], px)
        current_candle["low"]   = min(current_candle["low"],  px)
        current_candle["close"] = px

    # Stop-loss check on every tick
    if position and position["entry_price"] and not position["sell_id"]:
        if px <= position["entry_price"] - STOP_LOSS_PTS:
            place_sell(quote, "stop_loss")

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    fix.connect()
    if not _fix_ready.wait(timeout=60):
        log("FIX login timed out")
        os._exit(1)

    redis = RedisMarketDataClient(
        host=os.getenv("MARKET_REDIS_HOST", "52.76.242.46"),
        port=int(os.getenv("MARKET_REDIS_PORT", "6380")),
        password=os.getenv("MARKET_REDIS_PASSWORD", "Vn9ZMBF5SLafGkqEWc4h3b"),
        merge_updates=True,
    )

    log(f"Subscribing to {REDIS_SYMBOL} ...")
    await redis.subscribe(REDIS_SYMBOL, on_quote)
    log(f"Live — need {BB_WINDOW+1} candles before first signal (~{BB_WINDOW+1} min)")

    try:
        while True:
            await asyncio.sleep(1)
            if trades_done >= MAX_TRADES:
                log(f"Done! Reached {MAX_TRADES} trades.")
                break
            if datetime.now().time() >= time(14, 31):
                log(f"Market closed. Trades: {trades_done}")
                break
    except KeyboardInterrupt:
        log("Stopped")
    finally:
        fix.disconnect()
        os._exit(0)

if __name__ == "__main__":
    asyncio.run(main())
