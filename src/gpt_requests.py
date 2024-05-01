from typing import Dict

import loguru
import requests


def gpt_async_request(aspect: str, review: str, logger) -> Dict:
    prompt = {
        "modelUri": "gpt://b1gadu21mkrkragvdrks/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.05,
            "maxTokens": "2000"
        },

        "messages": [
            {
                "role": "system",
                "text": f'''Использовать форматирование тебе можно только для списка. Говори коротко и используй только мнение из текста. Обязательно сохраняй исходный порядок слов. Можешь выделять конкретные фразы, а не предложения.
Тебе дана рецензия на фильм. Если в рецензии нет {aspect}, то ответь только "None" и игнорируй текст дальше.
Если есть {aspect}, то выпиши из неё только эти части текста, в которых он встречается. (Пересказывать и вставлять комментарии запрещено, только выписывать имеющиеся части текста!) В ответе запиши список или просто "None".'''
            },
            {
                "role": "user",
                "text": review
            }
        ]
    }

    logger.debug(prompt)

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Api-Key AQVN0i1MKvzEFTe8os1PTN6D9zZ0RqTnJkXNh99y"
    }

    response = requests.post(url, headers=headers, json=prompt)
    logger.debug(f'{response.status_code} | {response.json()}')

    return response.json()


def gpt_answer(request_id: str, logger) -> Dict:
    url = "https://llm.api.cloud.yandex.net/operations/" + request_id
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Api-Key AQVN0i1MKvzEFTe8os1PTN6D9zZ0RqTnJkXNh99y"
    }

    response = requests.get(url, headers=headers)

    logger.debug(f'{response.status_code} | {response.json()}')

    return response.json()['response']['alternatives'][0]['message']['text']
