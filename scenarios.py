def apply_scenario(predictions, scenario):
    """
    Применяет сценарий к прогнозу.
    Базовый: без изменений.
    Оптимистичный: прогноз увеличивается на 10% (как если бы доходы выросли).
    Пессимистичный: прогноз уменьшается на 10% (как если бы расходы выросли).
    """
    if scenario == "Оптимистичный":
        return [p * 1.1 for p in predictions]
    elif scenario == "Пессимистичный":
        return [p * 0.9 for p in predictions]
    else:  # Базовый
        return predictions
