import datetime
from random import choice
from typing import Union

import pandas as pd
import telebot
from hydra import compose, initialize
from omegaconf import OmegaConf
from telebot import types

from utils import get_topics

_version = '1.1'
_job_name = "telegram_markup"
with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
    cfg = compose(config_name="config.yaml")

with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
    tg_cfg = compose(config_name="telegram_config.yaml")

print(OmegaConf.to_yaml(cfg))


ready_markup: Union[pd.DataFrame, None] = None

is_initialized = False

bot = telebot.TeleBot(tg_cfg['api_token'], parse_mode='MARKDOWN')

reviews = pd.read_csv(cfg['reviews_path'], index_col=0)['review']

CHAT_ID: Union[str, None] = tg_cfg['default_chat_id']


@bot.message_handler(commands=['start'])
def start_message(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    print(CHAT_ID)
    bot.send_message(message.chat.id, text=f'Hello.')
    help_message()


@bot.message_handler(commands=['help'])
def help_message(message: Union[None, types.Message] = None):
    global CHAT_ID
    bot.send_message(
        CHAT_ID, text=r'''   
        This bot is for crowd-source mark-up.    
        /start  -  to show start message. 
        /help   -  to show this message.
        /init   -  to initialize mark-up process. 
        /start\_markup  -  to start mark-up process.    
        /save\_work  -  to save current progress.
        '''
    )


@bot.message_handler(commands=['init'])
def init_markup(message):
    global is_initialized
    if is_initialized:
        bot.send_message(message.chat.id, text=f'Mark-up process has already been initialized.')
        return

    bot.send_message(message.chat.id, text=f'Initializing markup process...')

    global ready_markup
    ready_markup = pd.read_csv(cfg['gold_markup_path'])

    bot.send_message(message.chat.id, text=f'Done!')
    is_initialized = True


cur_review = None
cur_aspects = None


@bot.message_handler(commands=['start_markup'])
def process_review_aspect(message):
    global is_initialized
    if not is_initialized:
        bot.send_message(message.chat.id, text=f'First, you should initialize mark-up process by /init.')
        return

    global ready_markup
    if message.text in ('/stop', '/help', '/save_work'):
        ready_markup.drop(index=len(ready_markup) - 1, inplace=True)
        if message.text == '/save_work':
            save_message()
        return

    elif message.text != '/start_markup':
        process_answer(message.text)

    asp_review, topic, review = None, None, None
    global cur_aspects, cur_review

    if cur_aspects is None or len(cur_aspects) == 0:
        cur_aspects = get_topics()

        while review is None or len(review) > 4090:
            # Не очень оптимально, что не удаляем заведомо некорректные пары.
            review = choice(reviews)
        cur_review = review

    topic = cur_aspects.iloc[0]
    cur_aspects = cur_aspects.iloc[1:]

    asp_review = f'{telebot.formatting.mbold(topic)}\n\n{cur_review}'
    bot.send_message(message.chat.id, f'Длина следующего сообщения: {len(asp_review)} символов')
    msg = bot.send_message(message.chat.id, asp_review)

    ready_markup.loc[len(ready_markup.index)] = [topic, cur_review, None]

    bot.register_next_step_handler(msg, process_review_aspect)


@bot.message_handler(commands=['save_work'])
def save_message(message: Union[None, types.Message] = None):
    global is_initialized, CHAT_ID
    if not is_initialized:
        bot.send_message(CHAT_ID, text=f'First, you should initialize mark-up process by /init.')
        return

    global ready_markup
    ready_markup.to_csv(cfg['gold_markup_path'][:-3] +
                        str(datetime.datetime.now().strftime('%d.%m.%Y_%H-%M-%S')) +
                        cfg['gold_markup_path'][-4:],
                        index=False)

    bot.send_message(CHAT_ID, text=f'Progress have been saved.')


def process_answer(answer: str) -> None:
    answer = set(answer.split('\n'))
    print(answer)
    ready_markup.iat[-1, -1] = answer
    return


# bot.send_message(CHAT_ID, text=f'Bot started.')
# help_message()
print('Bot started.')
bot.polling(none_stop=True)
