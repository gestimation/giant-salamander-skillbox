"""Distribution helpers using only the Python standard library."""

from statistics import NormalDist


def normal_quantile(probability: float) -> float:
    if not 0.0 < probability < 1.0:
        raise ValueError("normal quantile probability must be strictly between 0 and 1")
    return NormalDist().inv_cdf(probability)


def critical_values(alpha: float, power: float, sides: int) -> tuple[float, float]:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1")
    if not 0.0 < power < 1.0:
        raise ValueError("power must be strictly between 0 and 1")
    if sides not in (1, 2):
        raise ValueError("sides must be 1 or 2")
    return normal_quantile(1.0 - alpha / sides), normal_quantile(power)
