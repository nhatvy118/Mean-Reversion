import time
from paperbroker.client import PaperBrokerClient

fix = PaperBrokerClient(
    default_sub_account="main",
    username="Group07",
    password="U13tC8z6H8tO",
    rest_base_url="https://papertrade.algotrade.vn/accounting",
    socket_connect_host="papertrade.algotrade.vn",
    socket_connect_port=5001,
    sender_comp_id="cf030e89c06043adbcd53a5b240a8910",
    target_comp_id="SERVER",
    console=True,
)

fix.connect()
time.sleep(3)
print("Sending logout...")
fix.disconnect()
time.sleep(2)
print("Done.")
import os; os._exit(0)
