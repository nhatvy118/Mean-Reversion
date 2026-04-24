import asyncio
import os
import sys
from datetime import datetime, time
from threading import Event as ThreadEvent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from paperbroker.client import PaperBrokerClient
from paperbroker.market_data import RedisMarketDataClient

# ── Config ────────────────────────────────────────────────────────────────────
REDIS_SYMBOL   = "HNXDS:VN30F2605"
FIX_SYMBOL     = "HNXDS:VN30F2605"
MAX_TRADES     = 30
TRADE_INTERVAL = 300   # place a new BUY every 5 minutes
TRADING_START  = time(9, 0)
FORCE_CLOSE    = time(14, 29)

_fix_ready  = ThreadEvent()
_buy_filled = ThreadEvent()

# ── State ─────────────────────────────────────────────────────────────────────
trades_done    = 0
position       = None   # {'buy_id', 'entry_price', 'sell_id'}
last_quote     = None
last_trade_ts  = 0.0    # timestamp of last BUY trigger

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

def buy_price(q):
    return round(q.ask_price_1 or q.latest_matched_price, 1)

def sell_price(q):
    p = q.bid_price_1 or q.latest_matched_price
    return round(p - 0.1, 1)   # slightly below bid to guarantee fill

def place_buy():
    global position, last_trade_ts
    if last_quote is None:
        return
    price = buy_price(last_quote)
    cl_ord_id = fix.place_order(
        symbol=FIX_SYMBOL, side="BUY", quantity=1,
        price=price, order_type="LIMIT",
    )
    position = {"buy_id": cl_ord_id, "entry_price": None, "sell_id": None}
    last_trade_ts = datetime.now().timestamp()
    log(f"BUY order → {price}  [{trades_done+1}/{MAX_TRADES}]")

def place_sell(reason: str):
    global position
    if position is None or position.get("sell_id") or last_quote is None:
        return
    price = sell_price(last_quote)
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
        log(f"BUY filled @ {last_px}  [{trades_done}/{MAX_TRADES}]")
        _buy_filled.set()
        # Immediately exit
        place_sell("immediate_exit")
    elif position.get("sell_id") == cl_ord_id:
        entry = position.get("entry_price") or last_px
        log(f"SELL filled @ {last_px}  pnl={last_px - entry:+.1f} pts")
        position = None
        _buy_filled.clear()

def on_rejected(cl_ord_id, reason=None, **kw):
    global position
    log(f"Order REJECTED: {reason}")
    if position and position.get("buy_id") == cl_ord_id:
        position = None

fix.on("fix:logon", on_logon)
fix.on("fix:order:filled", on_fill)
fix.on("fix:order:rejected", on_rejected)

# ── Market Data ───────────────────────────────────────────────────────────────

def on_quote(instrument, quote):
    global last_quote
    if quote.latest_matched_price:
        last_quote = quote

# ── Main loop ─────────────────────────────────────────────────────────────────

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
    await redis.subscribe(REDIS_SYMBOL, on_quote)
    log(f"Subscribed to {REDIS_SYMBOL} — will trade every {TRADE_INTERVAL//60} min")

    # Wait for first quote
    while last_quote is None:
        await asyncio.sleep(0.5)
    log("Market data flowing — starting trade loop")

    try:
        while trades_done < MAX_TRADES:
            t = datetime.now().time()

            if t >= FORCE_CLOSE:
                # Force close any open position then stop
                if position and position["entry_price"] and not position["sell_id"]:
                    place_sell("force_close")
                log(f"Market closing. Trades done: {trades_done}")
                break

            if t < TRADING_START:
                await asyncio.sleep(1)
                continue

            now_ts = datetime.now().timestamp()
            since_last = now_ts - last_trade_ts

            # Fire a new BUY every TRADE_INTERVAL seconds if no open position
            if position is None and since_last >= TRADE_INTERVAL:
                place_buy()

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        log("Stopped")
    finally:
        fix.disconnect()
        os._exit(0)

if __name__ == "__main__":
    asyncio.run(main())
