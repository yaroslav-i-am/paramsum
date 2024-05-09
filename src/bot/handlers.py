import asyncio
from pathlib import Path
from random import choice
from time import sleep
from typing import Union, Dict

import sys

import pandas as pd
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.utils.markdown import hbold, hcode, hitalic, hblockquote
from hydra import initialize, compose
from .utils import MarkupSession, make_special_gold_markup_path, cfg

from aiogram.types import FSInputFile

import os

from ..utils import get_topics

print(os.getcwd())
print(__name__)


router = Router()


reviews_texts: Union[pd.Series, None] = None


@router.message(Command("accept"))
async def cmd_accept(message: Message, state: FSMContext, command: CommandObject):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    print(command.args)
    if command.args is not None and command.args == 'restart':
        await state.set_state(None)
        await message.answer(
            text='OK',
        )
        await cmd_start(message, state)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    response_text = ''
    if await state.get_state() in (MarkupSession.initialized, MarkupSession.just_start):
        response_text = 'Вы начали сначала.'

    elif await state.get_state() == MarkupSession.in_progress:
        response_text = 'У Вас есть несохранённый прогресс. Если Вы действительно хотите вернуться в начало, ' \
                        f'используйте команду {hbold("/accept restart")} для подтверждения.\n\n' \
                        f'В противном случае, продолжайте размечать данные.'
        await message.answer(
            text=response_text,
        )
        return

    elif await state.get_state() is None:
        response_text = 'Привет!'

    await state.set_data(
        {
            'is_initialized': False,
            'ready_markup_df': None,
            'chat_id': message.from_user.id,
            'current_gold_markup_path': None,
            'cur_review': None,
            'cur_aspects': None,
            'user_response': None
        }
    )

    await message.answer(
        text=response_text,
    )
    await state.set_state(MarkupSession.just_start)


@router.message(Command('help', 'man'))
async def cmd_help(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.answer(
        text="Это сообщение поможет разобраться с ботом.",
    )


@router.message(StateFilter(MarkupSession.just_start), Command('init'))
async def cmd_init(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.answer(
        text="Инициализация сессии...",
    )
    await state.update_data(
        {
            'is_initialized': True,
            'ready_markup_df': pd.DataFrame(columns=pd.read_csv(cfg['gold_markup_path'], nrows=0).columns),
            'current_gold_markup_path': make_special_gold_markup_path(cfg['gold_markup_path'],
                                                                      message.from_user.full_name,
                                                                      str(message.from_user.id))
        }
    )

    global reviews_texts
    if reviews_texts is None:
        reviews_texts = pd.read_csv(cfg['reviews_path'], index_col=0)['review']

    data = await state.get_data()
    await message.answer(
        text=f"Результат Вашей работы будет сохранён в файл: {hblockquote(data['current_gold_markup_path'].parts[-1])}",
    )

    await message.answer(
        text="Вы готовы к разметке данных.",
    )
    await state.set_state(MarkupSession.initialized)


@router.message(StateFilter(MarkupSession.initialized), Command('init'))
async def cmd_init(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.answer(
        text="Ваша сессия уже была проинициализирована.",
    )


@router.message(StateFilter(MarkupSession.initialized), Command('start_markup'))
async def cmd_start_markup_intro(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await state.update_data(
        {}
    )
    await message.answer(
        text="Вы начали разметку данных!",
    )
    await state.set_state(MarkupSession.in_progress)
    await cmd_start_markup_progress(message, state)


@router.message(StateFilter(MarkupSession.in_progress), Command('start_markup', 'init'))
async def cmd_start_markup_intro(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await state.update_data(
        {}
    )
    await message.answer(
        text="Вы продолжаете разметку данных!",
    )


@router.message(StateFilter(MarkupSession.in_progress), Command('save_progress'))
async def cmd_save_progress(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    data = await state.get_data()

    try:
        pd.DataFrame().to_csv(data['current_gold_markup_path'], index=False)
    except Exception as e:
        await message.answer(
            text="Ваша разметка не была сохранена.",
        )

        if __debug__:
            await message.answer(
                text=str(e),
            )

        return

    if len(data['ready_markup_df']) > 0:
        data['ready_markup_df'].drop(index=len(data['ready_markup_df']) - 1, inplace=True)
    data['ready_markup_df'].to_csv(data['current_gold_markup_path'], index=False)

    await state.update_data(
        {
            'ready_markup_df': data['ready_markup_df'],  # Во избежание потери информации.
            'current_gold_markup_path': make_special_gold_markup_path(cfg['gold_markup_path'],
                                                                      message.from_user.full_name,
                                                                      str(message.from_user.id)),
            'cur_review': None,
            'cur_aspects': None,
            'user_response': None
        }
    )
    await message.answer(
        text="Ваша разметка успешно сохранена.",
    )

    await message.answer_document(FSInputFile(data['current_gold_markup_path']))

    await state.set_state(MarkupSession.initialized)


@router.message(~StateFilter(MarkupSession.in_progress), Command('save_progress'))
async def cmd_save_progress(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.answer(
        text="У Вас нет текущего прогресса.",
    )


@router.message(StateFilter(MarkupSession.in_progress))
async def cmd_start_markup_progress(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    data: Dict = await state.get_data()

    if not message.text.startswith('/'):
        prev_answer = set(message.text.split('\n'))
        print(prev_answer)
        data['ready_markup_df'].iat[-1, -1] = prev_answer

    asp_review, topic, review = None, None, None




    if data['cur_aspects'] is None or len(data['cur_aspects']) == 0:
        data['cur_aspects'] = get_topics()

        while review is None or len(review) > 4090:
            review = choice(reviews_texts)

        data['cur_review'] = review

    topic: Union[str, None] = data['cur_aspects'].iloc[0]
    data['cur_aspects'] = data['cur_aspects'].iloc[1:]

    asp_review = f'{hbold(topic.capitalize())}\n\n{data["cur_review"]}'

    data['ready_markup_df'].loc[len(data['ready_markup_df'].index)] = [topic, data['cur_review'], None]

    await state.update_data(
        data
    )

    await message.answer(
        text=f'Длина следующего сообщения {len(asp_review)} символов.',
    )

    await message.answer(
        text=asp_review,
    )


@router.message(StateFilter(MarkupSession.just_start), Command('start_markup'))
async def cmd_start_markup_early(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.answer(
        text=f"Перед началом разметки необходимо проинициализировать сессию командой {hcode('/init')}.",
    )


print('Bot started', file=sys.stderr)

