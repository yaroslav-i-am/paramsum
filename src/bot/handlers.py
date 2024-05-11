import asyncio
from pathlib import Path
from random import choice
from time import sleep
from typing import Union, Dict

import sys

import pandas as pd
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReactionTypeEmoji
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.utils.markdown import hbold, hcode, hitalic, hblockquote
from aiogram.utils.media_group import MediaGroupBuilder
from hydra import initialize, compose
from .utils import MarkupSession, make_special_gold_markup_path, cfg, tg_cfg
from .text import *

from aiogram.types import FSInputFile

import os

from ..utils import get_topics

from loguru import logger

logger.add(
    Path(cfg['logging_dir'], 'handlers.log'),
    rotation='100 MB',
    encoding='UTF-8'
)

print(os.getcwd())
print(__name__)


router = Router()


reviews_texts: Union[pd.Series, None] = None


@router.message(Command("accept"))
async def cmd_accept(message: Message, state: FSMContext, command: CommandObject):
    if __debug__:
        print(command.args)
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    if command.args is not None and command.args == 'restart':
        await state.set_state(MarkupSession.initialized)
        await message.answer(
            text='OK',
        )
        await cmd_start(message, state)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    logger.info(f'User {message.from_user.full_name} by id {message.from_user.id} started (or tried to) Bot-interaction.')
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    response_text = ''
    if await state.get_state() in (MarkupSession.initialized, MarkupSession.just_start):
        response_text = 'Вы начали сначала. \nИспользуйте /init, чтобы проинициализировать сессию разметки!'
        await message.answer(
            text=response_text,
        )

    elif await state.get_state() == MarkupSession.in_progress:
        response_text = 'У Вас есть несохранённый прогресс. Если Вы действительно хотите вернуться в начало, ' \
                        f'используйте команду {hcode("/accept restart")} для подтверждения.\n\n' \
                        f'В противном случае продолжайте работу .'
        await message.answer(
            text=response_text,
        )
        return

    elif await state.get_state() is None:
        await message.answer(
            text=f'Приветствую!',
        )
        await cmd_info(message, state)
        await cmd_help(message, state)

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

    await state.set_state(MarkupSession.just_start)
    await message.react([ReactionTypeEmoji(emoji="👏")])


@router.message(Command('info'))
async def cmd_info(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.answer(
        text=info_message,
    )
    album_builder = MediaGroupBuilder(
        caption="Примеры разметки."
    )


    album_builder.add(
        type="photo",
        media=FSInputFile("src/bot/assets/f1.png")
    )
    album_builder.add(
        type="photo",
        media=FSInputFile("src/bot/assets/f2.png")
    )
    album_builder.add(
        type="photo",
        media=FSInputFile("src/bot/assets/f3.png")
    )
    album_builder.add(
        type="photo",
        media=FSInputFile("src/bot/assets/f4.png")
    )
    await message.answer_media_group(
        media=album_builder.build()
    )


@router.message(Command('help'))
async def cmd_help(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.answer(
        text=help_message,
    )


@router.message(StateFilter(MarkupSession.just_start), Command('init'))
async def cmd_init(message: Message, state: FSMContext):
    logger.info(
        f'User {message.from_user.full_name} by id {message.from_user.id} attempted to init from start.')
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
            'ready_markup_df': pd.DataFrame(columns=pd.read_csv(cfg['gold_markup_path'], nrows=0).columns.tolist() +
                                            ['message_id']),
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

    await message.react([ReactionTypeEmoji(emoji="🎉")])
    await message.answer(
        text="Вы готовы к разметке данных. /start_markup, чтобы начать.",
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
        text="Ваша сессия уже была проинициализирована. /start_markup, чтобы начать разметку.",
    )


@router.message(StateFilter(MarkupSession.initialized), Command('start_markup'))
async def cmd_start_markup_intro(message: Message, state: FSMContext):
    logger.info(
        f'User {message.from_user.full_name} by id {message.from_user.id} started markup from initialized.')
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
    logger.info(
        f'User {message.from_user.full_name} by id {message.from_user.id} attempted to save existing progress.')
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

    if len(data['ready_markup_df']) > 0 and data['ready_markup_df'].iloc[-1, -1] is None:
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
        text="Ваша разметка успешно сохранена!",
    )

    await message.react([ReactionTypeEmoji(emoji="🔥")])

    await message.answer_document(
        FSInputFile(data['current_gold_markup_path']),
        caption='Файл никуда отправлять не нужно. Спасибо! :)'
    )

    await message.answer(
        text="Большая благодарность за помощь и участие в проекте!",
    )

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
    logger.info(
        f'User {message.from_user.full_name} by id {message.from_user.id} attempted to have progress in markup.')
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    data: Dict = await state.get_data()

    if not message.text.startswith('/'):
        prev_answer = set(message.text.split('\n'))
        print(prev_answer)
        data['ready_markup_df'].iat[-1, -2] = prev_answer
        data['ready_markup_df'].iat[-1, -1] = message.message_id

    asp_review, topic, review = None, None, None

    if data['cur_aspects'] is None or len(data['cur_aspects']) == 0:
        data['cur_aspects'] = get_topics()

        while review is None or len(review) > tg_cfg['max_message_len'] - get_topics().str.len().max():
            review = choice(reviews_texts)

        data['cur_review'] = review

    topic: Union[str, None] = data['cur_aspects'].iloc[0]
    data['cur_aspects'] = data['cur_aspects'].iloc[1:]

    asp_review = f'{hbold(topic.capitalize())}\n\n{data["cur_review"]}'

    data['ready_markup_df'].loc[len(data['ready_markup_df'].index)] = [topic, data['cur_review'], None, None]

    await state.update_data(
        data
    )

    await message.answer(
        text=f'Длина рецензии в символах: ≈{len(asp_review)}.',
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
        text=f"Перед началом разметки необходимо проинициализировать сессию командой /init.",
    )


@router.message(StateFilter(None))
async def cmd_some_start(message: Message, state: FSMContext):
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    await message.react([ReactionTypeEmoji(emoji="👏")])
    await message.answer(
        text=f"Спасибо, что пришли! Начните с команды /start.",
    )


@router.edited_message()
async def on_edited_message(message: Message, state: FSMContext):
    logger.info(
        f'User {message.from_user.full_name} by id {message.from_user.id} attempted to edit some message')
    if __debug__:
        await message.answer(
            text=str(await state.get_state()) + '\n' + str(await state.get_data()),
            parse_mode=None
        )

    data = await state.get_data()

    # print(data['ready_markup_df']['message_id'].values)
    # print(data['ready_markup_df']['message_id'])
    print(data['ready_markup_df'])

    if data['ready_markup_df'] is not None and message.message_id in data['ready_markup_df']['message_id'].values:
        ind = data['ready_markup_df'].query('message_id == @message.message_id').index

        data['ready_markup_df'].loc[ind, "answers"] = set(message.text.split('\n'))

        await message.reply(
            text=f"Редактирование было применено к разметке! 🔥\n"
                 f"Не забудьте сохранить изменения.",
        )
        await state.set_state(MarkupSession.in_progress)
    elif message.text.startswith('/'):
        await message.reply(
            text='Изменения сообщений, содержащих команд, не имеет последствий.'
        )
    else:
        await message.reply(
            text=f"Редактирование не было применено разметке :(\n"
                 f"Это случилось, потому что сессия, в рамках которой был Ваш ответ, была полностью завершена. ",
        )


print('Bot started', file=sys.stderr)

