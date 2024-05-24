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

_version = '1.1'
_job_name = "saiga_llama3_markup_recv"
with initialize(version_base=_version, config_path="../../cfg", job_name=_job_name):
    cfg = compose(config_name="config.yaml")

print(OmegaConf.to_yaml(cfg))

logger.add(
    Path(cfg['logging_dir'], 'saiga_llama3_labelling.log'),
    rotation='100 MB',
    encoding='UTF-8'
)

labelled_aspects = pd.read_csv(cfg['gold_markup_path'])
print(labelled_aspects)

aspect_adapter = {v: v for v in get_topics()}
aspect_adapter['описание игры актёров'] = 'описание игры актёров, мнение об актёре или то, как получился персонаж'


###################################################################################################################################
from llama_cpp import Llama

MODEL_NAME = "IlyaGusev/saiga_llama3_8b_gguf"
model_params = {
    'model_path': './models/model-q8_0.gguf',
    'n_ctx': 8192,
}
generation_params = {
    'top_k': 40,
    'top_p': 0.95,
    'temperature': cfg['temperature'],
    'repeat_penalty': 1.1,
}

logger.debug(f'{MODEL_NAME = }')

# Загружаем модель

model = Llama(
    model_path=model_params['model_path'],
    n_ctx=model_params['n_ctx'],
    n_parts=1,
    verbose=True,
)

logger.debug(f'Model initialized.')




###################################################################################################################################
logger.debug('Ready to generate')

llama3_responses = []

N_REVIEWS = 99
# for i in trange(labelled_aspects.shape[0]):
for i in trange(N_REVIEWS):
    row = labelled_aspects.iloc[i, :]
    aspect = aspect_adapter[row['aspect']]
    review = row['review']

    system_text = f'Использовать форматирование тебе можно только для списка. Говори коротко и используй только '\
                f'мнение из текста. Обязательно сохраняй исходный порядок слов. Можешь выделять конкретные '\
                f'фразы, а не предложения. \n'\
                f'Тебе дана рецензия на фильм. Если в рецензии нет {aspect}, то ответь '\
                f'только "None" и игнорируй текст дальше. Если есть {aspect}, то выпиши из неё только эти части '\
                f'текста, в которых он встречается. (Пересказывать и вставлять комментарии запрещено, только '\
                f'выписывать имеющиеся части текста!) В ответе запиши список или просто "None".'
    user_text = review

    messages = [{"role": "system", "content": system_text}, {"role": "user", "content": review}]

    logger.debug(f'{messages = }')

    text_response_parts = []

    for part in tqdm(model.create_chat_completion(
            messages=messages,
            temperature=generation_params['temperature'],
            top_k=generation_params['top_k'],
            top_p=generation_params['top_p'],
            repeat_penalty=generation_params['repeat_penalty'],
            stream=True,
    )):
        # print(f'{part = }')
        delta = part["choices"][0]["delta"]
        if "content" in delta:
            text_response_parts.append(delta['content'])

    answer = ''.join(text_response_parts)
    logger.debug(f'{answer = }')

    llama3_responses.append(answer)

saiga_markup_df = pd.read_csv(cfg['gold_markup_path']).iloc[:N_REVIEWS, :]
saiga_markup_df['gpt_markup'] = llama3_responses
saiga_markup_df.to_csv(cfg['silver_markup_path'], index=False)
