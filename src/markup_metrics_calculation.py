import evaluate
import pandas as pd
import numpy as np

import re
from pathlib import Path

from loguru import logger

import hydra
from hydra import compose, initialize
from omegaconf import OmegaConf

from tqdm import tqdm

tqdm.pandas()

_version = '1.1'
_job_name = "markup_metrics_calculation_job"
with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
    cfg = compose(config_name="config.yaml")

print(OmegaConf.to_yaml(cfg))

logger.add(
    Path(cfg['logging_dir'], 'markup_metrics_calculation.log'),
    rotation='100 MB',
    encoding='UTF-8'
)

markup = pd.read_csv(cfg['silver_markup_parsed_path'])
logger.debug(f'{markup.shape = }')

markup['gpt_markup_preprocessed'] = markup['gpt_markup_preprocessed'].fillna("{'-'}")


def get_metric_concat_sets(row: pd.Series, metric):
    params = {}
    if metric.name == 'chrf':
        params['word_order'] = 0
    elif metric.name == 'bert_score':
        params['lang'] = 'ru'

    val = metric.compute(predictions=[' '.join(row['gpt_markup_preprocessed'])], references=[' '.join(row['answers'])],
                         **params)
    return val


for cur_metr in ['bertscore', 'chrf', 'rouge', 'bleu']:
    print(cur_metr)
    metric = evaluate.load(cur_metr)
    metr_values = markup.progress_apply(get_metric_concat_sets, axis=1, args=(metric,))
    markup[f'concat_full_{cur_metr}'] = metr_values

logger.debug('markup:\n', markup)


def parse_concat_metrics(row: pd.Series, metric_name: str, sub_metric_name: str):
    if metric_name == 'bert_score':
        metric_name = 'bertscore'
    full_metric = row[f'concat_full_{metric_name}']
    return full_metric[sub_metric_name][0] \
        if isinstance(full_metric[sub_metric_name], list) \
        else full_metric[sub_metric_name]


sub_metrics_mapping = {
    'bert_score': ['precision', 'recall', 'f1'],
    'chrf': ['score'],
    'rouge': ['rouge1', 'rouge2', 'rougeL', 'rougeLsum'],
    'bleu': ['bleu', 'brevity_penalty']
}

for metric_name in ['bert_score', 'chrf', 'rouge', 'bleu']:
    print(metric_name)
    for sub_metric_name in sub_metrics_mapping[metric_name]:
        metr_values = markup.progress_apply(parse_concat_metrics, axis=1, args=(metric_name, sub_metric_name))
        new_column_name = f'concat_{sub_metric_name}' \
            if (metric_name in sub_metric_name) or (sub_metric_name in metric_name) \
            else f'concat_{sub_metric_name}_{metric_name}'
        markup[new_column_name] = metr_values


markup.to_csv(cfg['silver_markup_parsed_with_metrics_path'], index=False)
