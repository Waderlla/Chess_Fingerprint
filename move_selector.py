import random


def _normalize(weights):
    # Normalizuje listę wag do sumy 1.
    total = sum(weights)
    if total <= 0:
        return [1 / len(weights)] * len(weights)
    return [w / total for w in weights]


def choose_move_by_style(candidates, profile):
    # Wybiera ruch z TOP-3 propozycji silnika zgodnie z profilem stylu.
    if not candidates:
        return None

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    candidates = candidates[: min(len(candidates), 3)]

    precision = float(profile.get("precision_bias", 0.5) or 0.5)
    tactical = float(profile.get("tactical_bias", 0.5) or 0.5)
    aggression = float(profile.get("aggression_bias", 0.5) or 0.5)

    first = 0.45 + precision * 0.35 - aggression * 0.10
    second = 0.30 + tactical * 0.10
    third = 1.0 - first - second

    weights = [first, second, third][: len(candidates)]
    weights = [max(0.05, w) for w in weights]
    weights = _normalize(weights)

    chosen = random.choices(candidates, weights=weights, k=1)[0]
    return chosen["move"]
