from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from api.webhook_telegram import router as telegram_router
import uvicorn

app = FastAPI(title="AgriAdvisor Bihar Bot")

app.include_router(telegram_router)

@app.get("/")
async def root():
    return {"status": "AgriAdvisor bot is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
