import requests
import time
from dotenv import load_dotenv
import os
import csv

# Load .env variables
load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN is not set in your .env file or environment.")
    print("Please follow these steps:")
    print("1. Open Telegram and search for @BotFather")
    print("2. Send /newbot and follow instructions to create a bot.")
    print("3. Copy the HTTP API token BotFather gives you.")
    print("4. Paste it into backend/.env like this: TELEGRAM_BOT_TOKEN=your_token_here")
    exit(1)

print("✅ Bot Token found!")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
try:
    me = requests.get(f"{API_URL}/getMe").json()
    if me.get("ok"):
        print(f"✅ Successfully connected to Bot: @{me['result']['username']}")
    else:
        print("❌ Invalid Bot Token. Please check your .env file.")
        exit(1)
except Exception as e:
    print(f"❌ Connection error: {e}")
    exit(1)

print("\n" + "="*50)
print("🛠️  Mechanic Telegram ID Setup  🛠️")
print("="*50)
print(f"To link your Telegram account to a mechanic:")
print(f"1. Open Telegram and search for @{me['result']['username']}")
print(f"2. Send any message to the bot (e.g. 'Hello')")
print(f"Waiting for your message... (Timeout in 60s)")

chat_id = None
timeout = 60
start_time = time.time()
offset = 0

while time.time() - start_time < timeout:
    res = requests.get(f"{API_URL}/getUpdates?offset={offset}").json()
    if res.get("ok") and len(res["result"]) > 0:
        for update in res["result"]:
            if "message" in update:
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                username = msg["chat"].get("username", msg["chat"].get("first_name", "User"))
                print(f"\n✅ Message received from {username}!")
                print(f"✅ Your Chat ID is: {chat_id}")
                
                # Automatically assign to first available mechanic as a demo
                mechanics_file = os.path.join("data", "mechanics.csv")
                try:
                    rows = []
                    with open(mechanics_file, "r") as f:
                        reader = csv.DictReader(f)
                        headers = reader.fieldnames
                        for row in reader:
                            rows.append(row)
                    
                    if rows:
                        rows[0]["telegram_chat_id"] = str(chat_id)
                        with open(mechanics_file, "w", newline="") as f:
                            writer = csv.DictWriter(f, fieldnames=headers)
                            writer.writeheader()
                            writer.writerows(rows)
                        print(f"✅ Automatically linked Chat ID {chat_id} to Mechanic {rows[0]['name']} ({rows[0]['mechanic_id']}) in mechanics.csv!")
                    
                except Exception as e:
                    print(f"Could not automatically update mechanics.csv: {e}")
                    print(f"Please manually add the chat ID {chat_id} to mechanics.csv under the 'telegram_chat_id' column.")
                
                print("\n🎉 Setup Complete! Next time you create a job card and assign it to this mechanic, they will receive a Telegram message.")
                exit(0)
            offset = update["update_id"] + 1
    time.sleep(2)

print("\n⏳ Timed out waiting for a message. Please run this script again when you are ready to send a message.")
