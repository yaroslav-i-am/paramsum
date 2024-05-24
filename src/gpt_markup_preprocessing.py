import re
from pathlib import Path

import numpy as np
import pandas as pd
from hydra import compose, initialize
from loguru import logger
from omegaconf import OmegaConf
from tqdm.auto import tqdm


def process_gpt_markup(line: str, logger):
    logger.debug('INITIAL LINE')
    logger.debug(line)

    if line in (None, np.nan) or 'None' in line:
        line = np.nan
    else:
        line = list(filter(lambda el: el if len(el) > 0 else None, line.split('\n')))
        line = list(map(lambda el: re.sub(r'^\* ', r'', el), line))
        line = list(map(lambda el: re.sub(r'^- ', r'', el), line))
        line = list(map(lambda el: re.sub(r'^— ', r'', el), line))
        line = list(map(lambda el: el.strip(), line))

        line = list(filter(lambda aspect_line: len(aspect_line.split()) >= 2, line))
        if not line:
            line = ['<SOME_ASPECT>']

        # if 'inference' in config_name and line == ['<SOME_ASPECT>']:
        #     line = ['-']

        # line = set(line)

    logger.debug('FINAL LINE')
    logger.debug(line)
    logger.debug('\n\n-----------------------------------------------\n')

    return line


if __name__ == '__main__':

    tqdm.pandas()
    _version = '1.1'
    _job_name = "gpt_markup_preprocessing_job"
    config_name = "inference_config.yaml"

    with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
        cfg = compose(config_name=config_name)

    print(OmegaConf.to_yaml(cfg))

    logger.add(
        Path(cfg['logging_dir'], 'gpt_markup_preprocessing.log'),
        rotation='100 MB',
        encoding='UTF-8'
    )
    gpt_markup = pd.read_csv(cfg['silver_markup_path'])


    logger.debug(f'{gpt_markup.shape = }')

    if 'inference' in config_name:
        gpt_markup = gpt_markup[~gpt_markup['gpt_markup'].str.contains('Давайте сменим тему?').fillna(False)]

    gpt_markup['gpt_markup_preprocessed'] = gpt_markup['gpt_markup'].progress_apply(process_gpt_markup, args=(logger,))

    if 'inference' in config_name:
        gpt_markup['gpt_markup_preprocessed'] = gpt_markup['gpt_markup_preprocessed'].fillna("['-']")
        gpt_markup = gpt_markup[gpt_markup['gpt_markup_preprocessed'].astype('str') != "['<SOME_ASPECT>']"]

    gpt_markup.to_csv(cfg['silver_markup_parsed_path'], index=False)
