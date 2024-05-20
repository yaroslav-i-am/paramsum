from pathlib import Path

import pandas as pd

import os

from hydra import initialize, compose
from loguru import logger
from omegaconf import OmegaConf


if __name__ == '__main__':
    _version = '1.1'
    _job_name = "merge_crowd_markups"
    with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
        cfg = compose(config_name="config.yaml")

    print(OmegaConf.to_yaml(cfg))

    logger.add(
        Path('./logs/merge_crowd_markups.log'),
        rotation='100 MB',
        encoding='UTF-8'
    )

    is_descending_order = True
    dataframes = []
    root = './data/working_dir/crowd_markups/'
    logger.info(f'Files are sorted in {"descending" if is_descending_order else "ascending"} order.')
    logger.info(f'Root directory: {root}.')

    for filename in sorted(os.listdir(root), reverse=is_descending_order):
        logger.info(f'File `{filename}` found.')
        cur_df = pd.read_csv(root + filename)
        cur_df['filename'] = filename
        dataframes.append(cur_df)

    # 9% faster than iterative concatenation
    all_markup = pd.concat(dataframes).reset_index(drop=True)
    # If one review was labelled by different persons.
    all_markup['user_id'] = all_markup['filename'].apply(lambda s: s.split('_')[0])
    all_markup = all_markup.drop_duplicates(subset=['aspect', 'review', 'user_id'])

    # Replace `sets` to `lists`
    all_markup['answers'] = all_markup['answers']\
        .str.replace('{', '[')\
        .str.replace('}', ']')

    all_markup['gpt_markup'] = all_markup['gpt_markup'] \
        .str.replace('{', '[') \
        .str.replace('}', ']')

    all_markup.to_csv(cfg['gold_markup_final_path'], index=False)
    logger.info(f'Final crowd markup of shape {all_markup.shape} is saved to `{cfg["gold_markup_final_path"]}`.')
