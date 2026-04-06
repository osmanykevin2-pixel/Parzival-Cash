from fastapi import FastAPI, Request, Header, HTTPException
from app.config import WEBHOOK_SECRET
from app.bot_logic import handle_update

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "message": "Backend del bot activo"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None)
):
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    update = await request.json()
    print("UPDATE COMPLETO:", update)

    await handle_update(update)

    return {"ok": True}