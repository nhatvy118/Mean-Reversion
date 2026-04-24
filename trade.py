from paperbroker.client import PaperBrokerClient

client = PaperBrokerClient(
    default_sub_account="D1",
    username="Group07",
    password="U13tC8z6H8t0",
    rest_base_url="https://papertrade.algotrade.vn/accounting",
    socket_connect_host="papertrade.algotrade.vn",
    socket_connect_port=5001,
    sender_comp_id="cf030e89c06043adbcd53a5b240a8910",
    target_comp_id="SERVER",
)

client.on("fix:logon", lambda session_id, **kw: print(f"Logged in: {session_id}"))
client.on("fix:logon_error", lambda **kw: print(f"Login failed: {kw}"))

client.connect()

if client.wait_until_logged_on(timeout=10):
    cash = client.get_cash_balance()
    print(f"Available cash: {cash.get('remainCash', 0):,.0f} VND")
    print(f"Connection successful!")
else:
    print("Login timed out — check host/port/credentials")

client.disconnect()
