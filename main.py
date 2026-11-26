import os
import requests

TOKEN = os.getenv("KITOB_BOT_TOKEN")
CHAT_ID = os.getenv("KITOB_CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text
        }
    )

    print(response.text)


if __name__ == "__main__":
    if not TOKEN or not CHAT_ID:
        raise ValueError("Bot token yoki kanal ID topilmadi")

    send_message("Бот ишга тушди! ☺️")
