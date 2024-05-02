import re
from pathlib import Path

import numpy as np
import pandas as pd
from hydra import compose, initialize
from loguru import logger
from omegaconf import OmegaConf

_version = '1.1'
_job_name = "gpt_markup_preprocessing_job"
with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
    cfg = compose(config_name="config.yaml")

print(OmegaConf.to_yaml(cfg))

logger.add(
    Path(cfg['logging_dir'], 'gpt_markup_preprocessing.log'),
    rotation='100 MB',
    encoding='UTF-8'
)

gpt_markup = pd.read_csv(cfg['silver_markup_path'])
logger.debug(f'{gpt_markup.shape = }')


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

        line = set(line)

    logger.debug('FINAL LINE')
    logger.debug(line)
    logger.debug('\n\n-----------------------------------------------\n')

    return line


gpt_markup['gpt_markup_preprocessed'] = gpt_markup['gpt_markup'].apply(process_gpt_markup, args=(logger,))
gpt_markup.to_csv(cfg['silver_markup_parsed_path'], index=False)
