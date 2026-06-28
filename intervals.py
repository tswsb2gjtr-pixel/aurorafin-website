def add_intervals(predictions, confidence=0.15):
    """Добавляет доверительные интервалы (по умолчанию ±15%)"""
    lower = [p * (1 - confidence) for p in predictions]
    upper = [p * (1 + confidence) for p in predictions]
    return lower, upper
