from time import sleep
from typing import Dict

import pandas as pd
from loguru import logger
from tqdm import trange
from gpt_requests import gpt_async_request, gpt_answer
from utils import get_topics
from config import logs_dir
from pathlib import Path

logger.add(
    Path(logs_dir, 'gpt_requests.log'),
    rotation='100 MB',
    encoding='UTF-8'
)

id_filename = '../async_ids.txt'
id_file = open(id_filename, 'wt')

labelled_aspects = pd.read_csv(input('Enter filename of labelled aspects: '))
print(labelled_aspects)

aspect_adapter = {v: v for v in get_topics()}
aspect_adapter['описание игры актёров'] = 'описание игры актёров, мнение об актёре или то, как получился персонаж'


# for i in trange(labelled_aspects.shape[0]):
for i in trange(20):
    row = labelled_aspects.iloc[i, :]
    aspect = row['aspect']
    review = row['review']

    response: Dict = gpt_async_request(aspect_adapter[aspect], review, logger)
    id_file.write(response.get('id') + '\n')
    sleep(3)

id_file.close()

logger.debug('Waiting for the answer...')
sleep(60)

gpt_responses = []
gpt_markup_filename = '../data/working_dir/gpt_markup.csv'

with open(id_filename, 'rt') as id_file:
    for req_id in id_file.readlines():
        answer: Dict = gpt_answer(req_id.strip(), logger)
        gpt_responses.append(answer)

gpt_markup_df = pd.DataFrame()
gpt_markup_df['gpt_markup'] = gpt_responses
gpt_markup_df.to_csv(gpt_markup_filename, index=False)
