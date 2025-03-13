from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import httpx
from src.config import get_settings
import requests
import asyncio
import logging

settings = get_settings()
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
tx_cache = {}
logger = logging.getLogger(__name__)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Welcome to chAIrman bot! You can start chatting, "
        "and I'll forward your messages to the AI."
    )

@dp.message()
async def handle_message(message: types.Message):
    async with httpx.AsyncClient() as client:
        response = await client.post("YOUR_CHATBOT_ENDPOINT", json={"message": message.text})
        await message.answer(response.json()["response"])

async def send_tx_confirmation(tx_hash: str):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirm", callback_data=f"c_{tx_hash[:32]}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"r_{tx_hash[:32]}")
            ]
        ]
    )
    tx_cache[tx_hash[:32]] = tx_hash
    for admin_id in settings.ADMIN_IDS:
        await bot.send_message(
            chat_id=admin_id,
            text=f"Please confirm the transaction for buying Cow tokens!!! \n\n🔐 *Do you want to confirm safe transaction* `{tx_hash}`*?* ",
            reply_markup=keyboard,
            parse_mode="markdown"
        )

@dp.callback_query(lambda c: c.data.startswith(("c_", "r_")))
async def process_tx_callback(callback: types.CallbackQuery):
    try:
        action, short_hash = callback.data.split("_")
        tx_hash = tx_cache.get(short_hash)
        if not tx_hash:
            await callback.answer("Transaction expired or not found")
            return
        
        if action == "c":
            try:
                response = requests.post(
                    "http://localhost:3000/api/safe/confirm",
                    headers={
                        "accept": "application/json", 
                        "Content-Type": "application/json"
                    },
                    json={
                        "signer": settings.HUMAN_SIGNER_1_PRIVATE_KEY,
                        "safeAddress": settings.SAFE_ADDRESS,
                        "safeTxHash": tx_hash
                    }
                )
                response.raise_for_status()
                await callback.message.edit_text("✅ Transaction confirmed")
                
                # Wait 2 seconds
                await asyncio.sleep(2)
                
                # Get balance
                balance_response = requests.get(
                    "http://localhost:3000/api/safe/balance",
                    headers={"accept": "application/json"}
                )
                balance_data = balance_response.json()
                
                # Format balance message
                native_balance = float(balance_data["nativeBalance"]) / 10**18
                tokens_msg = []
                
                for token in balance_data["tokens"]:
                    if token["token"]:
                        balance = float(token["balance"]) / 10**18
                        symbol = token["token"]["symbol"]
                        tokens_msg.append(f"• {balance:.4f} {symbol}")
                    elif token["balance"]:
                        balance = float(token["balance"]) / 10**18
                        tokens_msg.append(f"• {balance:.4f} ETH")
                
                balance_msg = (
                    f"👝 *Safe Wallet*\n"
                    f"Native Balance: {native_balance:.4f} ETH\n"
                    f"\n*Tokens:*\n" + "\n".join(tokens_msg)
                )
                
                await callback.message.answer(balance_msg, parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to confirm transaction: {str(e)}")
        else:
            print("Transaction rejected")
        del tx_cache[short_hash]
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Error processing callback: {str(e)}")
