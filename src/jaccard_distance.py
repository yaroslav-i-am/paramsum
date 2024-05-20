from razdel import tokenize


def jaccard_distance(s1: str, s2: str) -> dict[str: float]:
    tokens1 = {token.text for token in tokenize(s1)}
    tokens2 = {token.text for token in tokenize(s2)}

    return {'score': len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))}


if __name__ == '__main__':
    str1 = 'Мама мыла раму'
    str2 = 'Мама мыла рому'

    print(jaccard_distance(str1, str2))