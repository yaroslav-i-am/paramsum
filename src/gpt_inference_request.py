import os
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
    _job_name = "gpt_inference_recv"
    with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
        cfg = compose(config_name="inference_config.yaml")

    with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
        yagpt_cfg = compose(config_name="yagpt_config.yaml")

    print(OmegaConf.to_yaml(cfg))

    logger.add(
        Path(cfg['logging_dir'], 'gpt_inference.log'),
        rotation='2048 MB',
        encoding='UTF-8'
    )

    all_reviews = pd.read_csv(cfg['reviews_path'])
    print(all_reviews)

    aspect_adapter = {v: v for v in get_topics()}
    aspect_adapter['описание игры актёров'] = 'описание игры актёров, мнение об актёре или то, как получился персонаж'

    N_REVIEWS_FROM_LABEL = 2
    N_REVIEWS_TO_LABEL = 1000

    id_filename = 'async_inference_ids.txt'

    model_id = yagpt_cfg['model_id'] if 'finetuned' in cfg['model_type'] else None

    for i in trange(N_REVIEWS_FROM_LABEL, N_REVIEWS_TO_LABEL):
        reviews_to_label = []
        aspects_to_extract = []
        gpt_markup = []

        review = all_reviews.iloc[i]['review']
        for aspect in get_topics().tolist():

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

            response_id = response.get('id')
            with open(id_filename, 'at') as id_file:
                id_file.write(response_id + '\n')
            logger.debug(f'ID {response_id} has been added to file.')

            reviews_to_label.append(review)
            aspects_to_extract.append(aspect)
            gpt_markup.append(response_id)
            sleep(1)

        out_markups_df = pd.DataFrame(data={
            'review': reviews_to_label,
            'aspect': aspects_to_extract,
            'gpt_markup': gpt_markup
        })
        out_markups_df.to_csv(cfg['out_path'], index=False, mode='a')

    logger.debug(f'{N_REVIEWS_FROM_LABEL} - {N_REVIEWS_TO_LABEL} reviews have been requested to labelling.')
