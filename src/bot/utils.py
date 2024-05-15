from pathlib import Path

from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from hydra import initialize, compose

import datetime

import re

_version = '1.1'
_job_name = "telegram_markup"
with initialize(version_base=_version, config_path="../../cfg", job_name=_job_name):
    cfg = compose(config_name="config.yaml")

with initialize(version_base=_version, config_path="../../cfg", job_name=_job_name):
    tg_cfg = compose(config_name="telegram_config.yaml")


class MarkupSession(StatesGroup):
    just_start = State()
    initialized = State()
    in_progress = State()


def make_special_gold_markup_path(gold_markup_path: str, full_name: str, user_id: str) -> Path:
    parts = list(Path(gold_markup_path).parts)
    parts.insert(-1, 'crowd_markups')
    parts[-1] = f'{user_id}_{datetime.datetime.now().strftime("%H-%M-%S_%d%m%Y")}_{parts[-1]}'
    path = str(Path(*parts))
    path = re.sub(r'\s', '_', path)
    return Path(path)
