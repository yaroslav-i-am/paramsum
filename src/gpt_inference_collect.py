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
        rotation='100 MB',
        encoding='UTF-8'
    )

    id_filename = 'async_inference_ids.txt'
    gpt_responses = []

    with open(id_filename, 'rt') as id_file:
        for req_id in tqdm(id_file.readlines()):
            try:
                answer: str = gpt_answer(req_id.strip(), yagpt_cfg['api-key'], logger)

            except Exception as e:
                logger.error(f'{e}')
                logger.error(f'{req_id}')
                answer = None

            with open('responses.txt', 'at') as f:
                f.write(repr(answer) + '\n')
            gpt_responses.append(answer)

    # temp_gpt_markup_df = pd.read_csv(cfg['part_out_path'])
    temp_gpt_markup_df = pd.DataFrame(columns=['ids', 'review', 'aspect', 'gpt_markup'])

    temp_gpt_markup_df['gpt_markup'] = gpt_responses
    with open(id_filename, 'rt') as id_file:
        temp_gpt_markup_df['ids'] = id_file.readlines()
    temp_gpt_markup_df.to_csv(cfg['part_out_path'], index=False)
    # temp_gpt_markup_df.to_csv(cfg['out_path'], index=False, mode='a' if os.path.exists(cfg['out_path']) else 'w')

    # os.remove(id_filename)
