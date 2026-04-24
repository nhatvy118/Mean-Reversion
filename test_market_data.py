"""
Quick test to verify market data is flowing correctly.
Prints the first 5 quotes then exits.

Usage:
  docker run --rm -v $(pwd):/app paperbroker-app python test_market_data.py redis
  docker run --rm -v $(pwd):/app paperbroker-app python test_market_data.py kafka
"""
import asyncio
import os
import sys

from paperbroker.market_data import RedisMarketDataClient, KafkaMarketDataClient

# Try all likely symbols to find which one has data
SYMBOLS_TO_TRY = [
    "HNXDS:VN30F2605",
    "HNXDS:VN30F2606",
    "HNXDS:VN30F2603",
    "HNXDS:VN30F2604",
]
SYMBOL    = "HNXDS:VN30F2605"
MAX_TICKS = 5

tick_count = 0

def on_quote(instrument, quote):
    global tick_count
    tick_count += 1
    print(f"\n── Tick #{tick_count} ──────────────────────────")
    print(f"  instrument : {instrument}")
    print(f"  price      : {quote.latest_matched_price}")
    print(f"  bid1/ask1  : {quote.bid_price_1} / {quote.ask_price_1}")
    print(f"  volume     : {quote.total_matched_quantity}")
    if tick_count >= MAX_TICKS:
        print(f"\n✅ Received {MAX_TICKS} ticks — market data is working!")
        os._exit(0)

async def test_redis():
    host = os.getenv("MARKET_REDIS_HOST", "52.76.242.46")
    port = int(os.getenv("MARKET_REDIS_PORT", "6380"))
    password = os.getenv("MARKET_REDIS_PASSWORD", "Vn9ZMBF5SLafGkqEWc4h3b")
    print(f"Testing REDIS  host: {host}:{port}\n")

    client = RedisMarketDataClient(
        host=host, port=port, password=password, merge_updates=True,
    )

    # ── Step 1: query latest cached price (works even outside market hours) ──
    print("Step 1 — querying latest cached price for each symbol:")
    for sym in SYMBOLS_TO_TRY:
        try:
            quote = await client.query(sym)
            if quote and quote.latest_matched_price:
                print(f"  ✅ {sym}  price={quote.latest_matched_price}  ← USE THIS SYMBOL")
            else:
                print(f"  ❌ {sym}  no data")
        except Exception as e:
            print(f"  ❌ {sym}  error: {e}")

    # ── Step 2: subscribe for live ticks ──────────────────────────────────────
    print(f"\nStep 2 — subscribing to {SYMBOL} for live ticks (60s)...")
    await client.subscribe(SYMBOL, on_quote)
    print("Waiting for ticks... (Ctrl+C to stop)")
    await asyncio.sleep(60)
    print("❌ No live ticks in 60s — market may be closed right now")
    print("   Vietnam market hours: 09:00-11:30 and 13:00-14:30")
    os._exit(1)

async def test_kafka():
    print(f"Testing KAFKA → {SYMBOL}")
    print(f"  servers: {os.getenv('PAPERBROKER_KAFKA_BOOTSTRAP_SERVERS', '52.77.119.94:9092')}")
    print(f"  env_id : {os.getenv('PAPERBROKER_ENV_ID', 'real')}\n")
    client = KafkaMarketDataClient(
        bootstrap_servers=os.getenv("PAPERBROKER_KAFKA_BOOTSTRAP_SERVERS", "52.77.119.94:9092"),
        username=os.getenv("PAPERBROKER_KAFKA_USERNAME", "username"),
        password=os.getenv("PAPERBROKER_KAFKA_PASSWORD", "password"),
        env_id=os.getenv("PAPERBROKER_ENV_ID", "real"),
        merge_updates=True,
    )
    await client.subscribe(SYMBOL, on_quote)
    await client.start()
    print("Waiting for ticks... (Ctrl+C to stop)")
    await asyncio.sleep(60)
    print("❌ No data received in 60s — check symbol or market hours")
    os._exit(1)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "redis"
    if mode == "kafka":
        asyncio.run(test_kafka())
    else:
        asyncio.run(test_redis())
