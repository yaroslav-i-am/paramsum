import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
import aiogram
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from .handlers import router, cfg, tg_cfg

from hydra import compose, initialize
from omegaconf import OmegaConf


import os
print(os.getcwd())
print(__name__)

import platform
if platform.system() == 'Linux':
    os.chdir(r'/home/pristalovya/documents/paramsum')
else:
    os.chdir(r'D:\Programming\Research\Thesis\paramsum')


print(OmegaConf.to_yaml(cfg))


async def main():
    bot = Bot(token=tg_cfg['api_token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
