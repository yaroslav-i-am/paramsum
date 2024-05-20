import ast
from pathlib import Path

import evaluate
import numpy as np
import pandas as pd
from hydra import compose, initialize
from loguru import logger
from omegaconf import OmegaConf
from tqdm import tqdm

from sklearn.metrics import classification_report

from jaccard_distance import jaccard_distance


def get_metric_concat_sets(row: pd.Series, metric):
    params = {}

    if hasattr(metric, 'name'):
        if metric.name == 'chrf':
            params['word_order'] = 2
        elif metric.name in ('bert_score', 'bertscore'):
            params['lang'] = 'ru'

    gpt_markup_preprocessed = ast.literal_eval(row['gpt_markup_preprocessed'])
    answers = ast.literal_eval(row['answers'])

    if hasattr(metric, 'name'):
        val = metric.compute(predictions=['. \n\n'.join(gpt_markup_preprocessed)], references=['. \n\n'.join(answers)],
                             **params)
    else:
        val = metric('. \n\n'.join(gpt_markup_preprocessed), '. \n\n'.join(answers))

    return val


def parse_concat_metrics(row: pd.Series, metric_name: str, sub_metric_name: str):
    if metric_name == 'bert_score':
        metric_name = 'bertscore'
    full_metric = row[f'concat_full_{metric_name}']
    return full_metric[sub_metric_name][0] \
        if isinstance(full_metric[sub_metric_name], list) \
        else full_metric[sub_metric_name]


if __name__ == '__main__':

    tqdm.pandas()

    _version = '1.1'
    _job_name = "markup_metrics_calculation_job"
    with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
        cfg = compose(config_name="config.yaml")

    print(OmegaConf.to_yaml(cfg))

    metr_file = open(cfg['metric_file'], 'wt', encoding='UTF-8')

    logger.add(
        Path(cfg['logging_dir'], 'markup_metrics_calculation.log'),
        rotation='100 MB',
        encoding='UTF-8'
    )

    markup = pd.read_csv(cfg['silver_markup_parsed_path'])
    logger.debug(f'{markup.shape = }')

    markup['gpt_markup_preprocessed'] = markup['gpt_markup_preprocessed'].fillna("['-']")

    markup['none_answers'] = markup['answers'] == "['-']"
    markup['none_markup'] = markup['gpt_markup_preprocessed'] == "['-']"

    logger.debug(f"{markup['none_answers'].sum()} отсутствий тематики в целевой переменной")
    logger.debug(f"{markup['none_markup'].sum()} отсутствий тематики в предсказанных значениях")

    print((markup['none_answers'] & markup['none_markup']).sum())
    print((markup['none_answers'] | markup['none_markup']).sum())

    metr_file.write(f"NO_ASPECT_IN_ANSWERS: {markup['none_answers'].sum()}\n")
    metr_file.write(f"NO_ASPECT_IN_MARKUP: {markup['none_markup'].sum()}\n")

    cr = classification_report(markup['none_answers'], markup['none_markup'], output_dict=True)

    metr_file.write(f"CLASS_MEAN_F1: {np.mean([cr['False']['f1-score'], cr['True']['f1-score']])}\n")
    metr_file.write(f"ACCURACY: {cr['accuracy']}\n")

    print(classification_report(markup['none_answers'], markup['none_markup']))

    logger.debug('Processing initial metrics calculation')
    for cur_metr in ['bertscore', 'chrf', 'jaccard']:
        print(cur_metr)
        if cur_metr == 'jaccard':
            metric = jaccard_distance
        else:
            metric = evaluate.load(cur_metr)
        metr_values = markup.progress_apply(get_metric_concat_sets, axis=1, args=(metric,))
        markup[f'concat_full_{cur_metr}'] = metr_values
    logger.debug('Finished initial metrics calculation')

    logger.debug(f'{markup.shape = }')

    sub_metrics_mapping = {
        'bert_score': ['precision', 'recall', 'f1'],
        'chrf': ['score'],  # chrF++
        'jaccard': ['score']
        # 'rouge': ['rouge1', 'rouge2', 'rougeL', 'rougeLsum'],
        # 'bleu': ['bleu', 'brevity_penalty']
    }

    logger.debug('Metrics postprocessing and parsing...')
    for metric_name in ['bert_score', 'chrf', 'jaccard']:
        print(metric_name)
        for sub_metric_name in sub_metrics_mapping[metric_name]:
            metr_values = markup.progress_apply(parse_concat_metrics, axis=1, args=(metric_name, sub_metric_name))
            new_column_name = f'concat_{sub_metric_name}' \
                if (metric_name in sub_metric_name) or (sub_metric_name in metric_name) \
                else f'concat_{sub_metric_name}_{metric_name}'
            markup[new_column_name] = metr_values
            metr_values_no_nones = metr_values[(markup['answers'] != "['-']") & (markup['gpt_markup_preprocessed'] != "['-']")]

            print(len(metr_values_no_nones))
            assert len(metr_values_no_nones) == (~(markup['none_answers'] | markup['none_markup'])).sum()

            metr_file.write(
                f'{new_column_name.upper()}_NO_NONES: {np.mean(metr_values_no_nones)}\n'
            )
            metr_file.write(
                f'{new_column_name.upper()}: {np.mean(metr_values)}\n'
            )
    logger.debug('Finished metrics postprocessing and parsing...')

    markup.to_csv(cfg['silver_markup_parsed_with_metrics_path'], index=False)

    metr_file.close()
