from typing import Dict

import requests


def gpt_async_request(
        aspect: str,
        model_subname: str,
        review: str,
        temperature: float,
        api_key: str,
        folder_id: str,
        logger,
        model_id: str = None,
) -> Dict:
    if 'finetuned' in model_subname:
        if model_id is None:
            raise AttributeError('Model is finetuned but model_id is not provided.')
        # Finetuned YaGPT
        model_uri = f"ds://{model_id}"
    else:
        # Default YaGPT
        model_uri = f"gpt://{folder_id}/yandex{model_subname}/latest",

    prompt = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": "2000"
        },

        "messages": [
            {
                "role": "system",
                "text": f'Использовать форматирование тебе можно только для списка. Говори коротко и используй только '
                        f'мнение из текста. Обязательно сохраняй исходный порядок слов. Можешь выделять конкретные '
                        f'фразы, а не предложения. \n'
                        f'Тебе дана рецензия на фильм. Если в рецензии нет {aspect}, то ответь '
                        f'только "None" и игнорируй текст дальше. Если есть {aspect}, то выпиши из неё только эти части '
                        f'текста, в которых он встречается. (Пересказывать и вставлять комментарии запрещено, только '
                        f'выписывать имеющиеся части текста!) В ответе запиши список или просто "None".'
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
        "Authorization": f"Api-Key {api_key}"
    }

    response = requests.post(url, headers=headers, json=prompt)
    logger.debug(f'{response.status_code} | {response.json()}')

    return response.json()


def gpt_answer(request_id: str, api_key: str, logger) -> str:
    url = "https://llm.api.cloud.yandex.net/operations/" + request_id
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}"
    }

    response = requests.get(url, headers=headers)

    logger.debug(f'{response.status_code} | {response.json()}')

    return response.json()['response']['alternatives'][0]['message']['text']
