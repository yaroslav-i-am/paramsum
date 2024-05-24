from pathlib import Path
from time import sleep
from typing import Dict

import pandas as pd
from hydra import compose, initialize
from loguru import logger
from omegaconf import OmegaConf
from tqdm import trange
from tqdm.auto import tqdm

from gpt_requests import gpt_async_request, gpt_answer
from utils import get_topics

if __name__ == '__main__':
    _version = '1.1'
    _job_name = "gpt_markup_recv"
    with initialize(version_base=_version, config_path="../../cfg", job_name=_job_name):
        cfg = compose(config_name="config.yaml")

    with initialize(version_base=_version, config_path="../../cfg", job_name=_job_name):
        yagpt_cfg = compose(config_name="yagpt_config.yaml")

    print(OmegaConf.to_yaml(cfg))

    logger.add(
        Path(cfg['logging_dir'], 'gpt_requests.log'),
        rotation='100 MB',
        encoding='UTF-8'
    )

    id_filename = 'async_ids.txt'
    id_file = open(id_filename, 'wt')

    labelled_aspects = pd.read_csv(cfg['gold_markup_path'])
    print(labelled_aspects)

    aspect_adapter = {v: v for v in get_topics()}
    aspect_adapter['описание игры актёров'] = 'описание игры актёров, мнение об актёре или то, как получился персонаж'

    model_id = yagpt_cfg['model_id'] if 'finetuned' in cfg['model_type'] else None

    # for i in trange(labelled_aspects.shape[0]):
    for i in trange(99):
        row = labelled_aspects.iloc[i, :]
        aspect = row['aspect']
        review = row['review']

        response: Dict = gpt_async_request(
            aspect_adapter[aspect],
            cfg['model_type'],
            review,
            float(cfg['temperature']),
            api_key=yagpt_cfg['api-key'],
            folder_id=yagpt_cfg['folder_id'],
            logger=logger,
            model_id=model_id
        )
        id_file.write(response.get('id') + '\n')
        sleep(1)

    id_file.close()

    logger.debug('Waiting for the answer...')
    sleep(120)

    gpt_responses = []

    with open(id_filename, 'rt') as id_file:
        for req_id in tqdm(id_file.readlines()):
            answer: str = gpt_answer(req_id.strip(), logger)
            gpt_responses.append(answer)

    gpt_markup_df = pd.read_csv(cfg['gold_markup_path'])
    gpt_markup_df['gpt_markup'] = gpt_responses
    gpt_markup_df.to_csv(cfg['silver_markup_path'], index=False)
