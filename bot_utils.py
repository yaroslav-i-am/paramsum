import pandas as pd


def get_reviews(reviews: pd.Series) -> pd.Series:
    reviews_path = './data/reviews.csv'
    reviews_series = pd.read_csv(reviews_path, index_col=0)['review']

    return reviews_series


def get_topics() -> pd.Series:
    topics = [
        'Описание игры актёров',
        'Описание характера актёров',
        'Описание характера персонажей',
        'Характеристика внешности актёров',
        'Характеристика внешности персонажей',
        'Эмоции от просмотра фильма',
        'Описание декораций',
    ]

    return pd.Series(topics)


def bold(s):
    return f'**{s}**'


def ital(s):
    return f'*{s}*'


# print(get_reviews())
