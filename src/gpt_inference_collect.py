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
        Path(cfg['logging_dir'], 'gpt_inference_collect.log'),
        rotation='2048 MB',
        encoding='UTF-8'
    )

    id_filename = 'async_inference_ids.txt'
    gpt_markup = pd.read_csv(cfg['part_out_path'])

    to_answer = []

    for i in tqdm(range(gpt_markup.shape[0])):
        req_id: str = gpt_markup.iloc[i]['gpt_markup'].strip()

        if not req_id.startswith('d7q'):
            logger.debug('Answer exists')
            continue

        try:
            answer: str = gpt_answer(req_id, yagpt_cfg['api-key'], logger)
        except Exception as e:
            logger.error(f'{e}')
            logger.error(f'{req_id}')
            to_answer.append(req_id)

        else:
            gpt_markup.iloc[i]['gpt_markup'] = answer
            if i % 100 == 0:
                gpt_markup.to_csv(cfg['silver_markup_path'], index=False)

    gpt_markup.to_csv(cfg['silver_markup_parsed_path'], index=False)
    os.remove(id_filename)
    print(*to_answer, sep='\n')
