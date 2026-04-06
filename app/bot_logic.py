import httpx
from app.config import TELEGRAM_BOT_TOKEN
from app.db import get_user, upsert_user

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            }
        )

async def handle_update(update: dict):
    print("ENTRO EN handle_update")

    message = update.get("message")
    if not message:
        return

    text = message.get("text", "")
    chat_id = message["chat"]["id"]

    from_user = message["from"]
    telegram_user_id = from_user["id"]
    telegram_username = from_user.get("username")

    print("TEXT:", text)
    print("USER ID:", telegram_user_id)

    if text.startswith("/start"):
        print("ENTRO EN /start")

        user = get_user(telegram_user_id)

        data = {
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username
        }

        upsert_user(data)

        await send_message(
            chat_id,
            "Bienvenido. Ya estás registrado en el sistema."
        )