from aiogram import Bot
from aiogram.types import BotCommand


async def set_bot_commands(bot: Bot):
    main_menu_commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="chat", description="Chat with ChAIrman")
    ]
    await bot.set_my_commands(main_menu_commands)
