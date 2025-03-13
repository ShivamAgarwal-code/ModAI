from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import asyncio
from typing import Dict
from pydantic import BaseModel
from src.bot import dp, bot, send_tx_confirmation
from src.config import get_settings
from src.utils.commands import set_bot_commands

bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task
    await set_bot_commands(bot)
    bot_task = asyncio.create_task(dp.start_polling(bot))
    yield
    if bot_task:
        bot_task.cancel()
        await bot.session.close()


app = FastAPI(title="chAIrman Service", lifespan=lifespan)
settings = get_settings()

class TransactionRequest(BaseModel):
    tx_hash: str

@app.post("/confirm-tx")
async def confirm_transaction(tx_request: TransactionRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_tx_confirmation, tx_request.tx_hash)
    return {"status": "confirmation request sent"}
