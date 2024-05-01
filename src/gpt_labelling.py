from time import sleep
from typing import Dict

import pandas as pd
from loguru import logger
from tqdm import trange
from gpt_requests import gpt_async_request, gpt_answer
from utils import get_topics
from pathlib import Path

import hydra
from hydra import compose, initialize
from omegaconf import OmegaConf

_version = '1.1'
_job_name = "gpt_markup_recv"
with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
    cfg = compose(config_name="config.yaml")

print(OmegaConf.to_yaml(cfg))

logger.add(
    Path(cfg['logging_dir'], 'gpt_requests.log'),
    rotation='100 MB',
    encoding='UTF-8'
)

id_filename = '../async_ids.txt'
id_file = open(id_filename, 'wt')

labelled_aspects = pd.read_csv(cfg['gold_markup_path'])
print(labelled_aspects)

aspect_adapter = {v: v for v in get_topics()}
aspect_adapter['описание игры актёров'] = 'описание игры актёров, мнение об актёре или то, как получился персонаж'


# for i in trange(labelled_aspects.shape[0]):
for i in trange(100):
    row = labelled_aspects.iloc[i, :]
    aspect = row['aspect']
    review = row['review']

    response: Dict = gpt_async_request(aspect_adapter[aspect], review, logger)
    id_file.write(response.get('id') + '\n')
    sleep(1)

id_file.close()

logger.debug('Waiting for the answer...')
sleep(60)

gpt_responses = []

with open(id_filename, 'rt') as id_file:
    for req_id in id_file.readlines():
        answer: Dict = gpt_answer(req_id.strip(), logger)
        gpt_responses.append(answer)

gpt_markup_df = pd.read_csv(cfg['gold_markup_path'])
gpt_markup_df['gpt_markup'] = gpt_responses
gpt_markup_df.to_csv(cfg['gpt_markup_path'], index=False)
