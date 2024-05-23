from pathlib import Path
from time import sleep
from typing import Dict

import pandas as pd
from hydra import compose, initialize
from loguru import logger
from omegaconf import OmegaConf
from tqdm import trange

from gpt_requests import gpt_async_request, gpt_answer
from utils import get_topics

_version = '1.1'
_job_name = "saiga_markup_recv"
with initialize(version_base=_version, config_path="../cfg", job_name=_job_name):
    cfg = compose(config_name="config.yaml")

print(OmegaConf.to_yaml(cfg))

logger.add(
    Path(cfg['logging_dir'], 'saiga_requests.log'),
    rotation='100 MB',
    encoding='UTF-8'
)

labelled_aspects = pd.read_csv(cfg['gold_markup_path'])
print(labelled_aspects)

aspect_adapter = {v: v for v in get_topics()}
aspect_adapter['описание игры актёров'] = 'описание игры актёров, мнение об актёре или то, как получился персонаж'


###################################################################################################################################
import torch
from peft import PeftModel, PeftConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

MODEL_NAME = "IlyaGusev/saiga_mistral_7b_lora"

logger.debug(f'{MODEL_NAME = }')

# Загружаем модель
config = PeftConfig.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    config.base_model_name_or_path,
    torch_dtype=torch.float16,
    device_map="auto",
    offload_folder="offload",
)
model = PeftModel.from_pretrained(
    model,
    MODEL_NAME,
    torch_dtype=torch.float16,
    offload_folder="offload",
)
model.eval()
logger.debug(f'Model initialized.')
model.to('cuda')
logger.debug(f'Model transferred to CUDA.')

# Определяем токенайзер
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)
generation_config = GenerationConfig.from_pretrained(MODEL_NAME)
print(generation_config)
generation_config.max_new_tokens = 2000
generation_config.temperature = cfg['temperature']

# Функция для обработки запросов
def generate(model, tokenizer, prompt, generation_config):
    data = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
    data = {k: v.to(model.device) for k, v in data.items()}
    output_ids = model.generate(
        **data,
        generation_config=generation_config
    )[0]
    output_ids = output_ids[len(data["input_ids"][0]):]
    output = tokenizer.decode(output_ids, skip_special_tokens=True)
    return output.strip()


###################################################################################################################################
logger.debug('Ready to generate')

saiga_responses = []

N_REVIEWS = 99
# for i in trange(labelled_aspects.shape[0]):
for i in trange(N_REVIEWS):
    row = labelled_aspects.iloc[i, :]
    aspect = aspect_adapter[row['aspect']]
    review = row['review']

    PROMT_TEMPLATE = '<s>system\n{system_text}</s><s>user\n{user_text}</s><s>bot\n'

    system_text = f'Использовать форматирование тебе можно только для списка. Говори коротко и используй только '\
                f'мнение из текста. Обязательно сохраняй исходный порядок слов. Можешь выделять конкретные '\
                f'фразы, а не предложения. \n'\
                f'Тебе дана рецензия на фильм. Если в рецензии нет {aspect}, то ответь '\
                f'только "None" и игнорируй текст дальше. Если есть {aspect}, то выпиши из неё только эти части '\
                f'текста, в которых он встречается. (Пересказывать и вставлять комментарии запрещено, только '\
                f'выписывать имеющиеся части текста!) В ответе запиши список или просто "None".'

    user_text = review

    inp = 'Какое расстояние до Луны?'
    prompt = PROMT_TEMPLATE.format(system_text=system_text, user_text=user_text)

    logger.debug(f'{prompt = }')

    answer = generate(model, tokenizer, prompt, generation_config)
    logger.debug(f'{answer = }')

    saiga_responses.append(answer)

saiga_markup_df = pd.read_csv(cfg['gold_markup_path']).iloc[:N_REVIEWS, :]
saiga_markup_df['gpt_markup'] = saiga_responses
saiga_markup_df.to_csv(cfg['silver_markup_path'], index=False)
