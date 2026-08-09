from typing import Iterable


def validate_score(score: float) -> float:
    if score < 1 or score > 10 or score * 2 != int(score * 2):
        raise ValueError("评分必须是1至10之间的0.5倍数")
    return score


def average_score(scores: Iterable[float]) -> tuple[float, int]:
    values = list(scores)
    if not values:
        return 0.0, 0
    return round(sum(values) / len(values), 2), len(values)
