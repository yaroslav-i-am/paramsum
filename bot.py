import datetime

import pandas as pd
import telebot
from random import choice
from bot_utils import get_reviews, get_topics
from typing import Union

markup_file: Union[pd.DataFrame, None] = None
ready_markup: Union[pd.DataFrame, None] = None

API_TOKEN = '7180019079:AAEg7oM0Kcq51-gxw5Fqg4RlyHeV9zH9xbA'

is_initialized = False

bot = telebot.TeleBot(API_TOKEN, parse_mode='MARKDOWN')

markup_filename = 'ready_markup.csv'

reviews_path = './data/reviews.csv'
reviews = pd.read_csv(reviews_path, index_col=0)['review']

CHAT_ID = '1247696527'


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, text=f'Hello')


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id, text='''   
    This bot is for crowd-source mark-up.    
    /start  -  to show start message. 
    /help   -  to show this message.
    /init   -  to initialize markup process. 
    /start\_markup  -  to start marking-up.    
    /save\_work  -  to save current progress.
    ''')


@bot.message_handler(commands=['init'])
def init_markup(message):
    global is_initialized
    if is_initialized:
        bot.send_message(message.chat.id, text=f'Mark-up process has already been initialized.')
        return

    bot.send_message(message.chat.id, text=f'Initializing markup process...')

    global markup_file, ready_markup, markup_filename
    ready_markup = pd.read_csv(markup_filename)

    bot.send_message(message.chat.id, text=f'Done!')
    is_initialized = True


@bot.message_handler(commands=['start_markup'])
def process_review_aspect(message):
    global is_initialized
    if not is_initialized:
        bot.send_message(message.chat.id, text=f'First, you should initialize mark-up process by /init.')
        return

    global ready_markup
    if message.text in ('/stop', '/help'):
        ready_markup.drop(index=len(ready_markup) - 1, inplace=True)
        return

    elif message.text != '/start_markup':
        process_answer(message.text)

    asp_review, topic, review = None, None, None

    while asp_review is None or len(asp_review) > 4096:
        # Не очень оптимально, что не удаляем заведомо некорректные пары.
        topic = choice(get_topics())
        review = choice(reviews)
        asp_review = f'{telebot.formatting.mbold(topic)}\n\n{review}'
    bot.send_message(message.chat.id, f'Длина следующего сообщения: {len(asp_review)} символов')
    msg = bot.send_message(message.chat.id, asp_review)

    ready_markup.loc[len(ready_markup.index)] = [topic, review, None]

    bot.register_next_step_handler(msg, process_review_aspect)


@bot.message_handler(commands=['save_work'])
def save_message(message):
    global is_initialized
    if not is_initialized:
        bot.send_message(message.chat.id, text=f'First, you should initialize mark-up process by /init.')
        return

    global ready_markup, markup_filename
    ready_markup.to_csv(markup_filename[:-3] +
                        str(datetime.datetime.now().strftime('%d.%m.%Y_%H-%M-%S')) +
                        markup_filename[-3:],
                        index=False)

    bot.send_message(message.chat.id, text=f'Progress have been saved.')


def process_answer(answer: str) -> None:
    print(answer)
    ready_markup.iloc[-1, -1] = answer
    return


bot.send_message(CHAT_ID, text=f'Bot started.')
print('Bot started.')
bot.polling(none_stop=True)
