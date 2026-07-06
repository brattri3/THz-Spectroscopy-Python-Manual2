import numpy as np

def normalize_angle_conditional(angle: float) -> float:
    """
    Приводит произвольный угол к симметричному диапазону [-180, 180] градусов
    с использованием классического логического ветвления (if/else).
    """
    # 1. Ограничиваем угол диапазоном [0, 360) градусов
    angle = angle % 360.0
    
    # 2. Если угол зашел во вторую половину круга, переводим в отрицательную шкалу
    if angle > 180.0:
        angle -= 360.0  # тождественно: angle = angle - 360.0
        
    return angle


def normalize_angle(angle: float) -> float:
    """
    Приводит произвольный угол к симметричному диапазону [-180, 180] градусов
    с использованием компактной арифметической формулы с остатком от деления.
    """
    return ((angle + 180.0) % 360.0) - 180.0


def get_signal_pair(
    db: dict, angle1: float, angle2: float, rep: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Извлекает из базы данных (db) пару сигналов: сигнал образца и сигнал фона,
    соответствующие заданным углам поляризаторов и номеру реплики.
    Возвращает кортеж (t_bg, E_bg, t_sig, E_sig).
    """
    sig_key = ('signal_raw', angle1, angle2, rep)
    bg_key = ('bg_raw', angle1, angle2, rep)
    
    if sig_key not in db:
        raise KeyError(f"Ключ сигнала {sig_key} отсутствует в базе данных.")
    if bg_key not in db:
        raise KeyError(f"Ключ фона {bg_key} отсутствует в базе данных.")
        
    t_sig, E_sig = db[sig_key]
    t_bg, E_bg = db[bg_key]
    
    return t_bg, E_bg, t_sig, E_sig


if __name__ == "__main__":
    # Быстрый тест работоспособности функций
    test_angles = [0.0, 90.0, 180.0, 270.0, 360.0, 730.0, -45.0]
    print("Проверка математической нормализации углов:")
    for a in test_angles:
        norm_cond = normalize_angle_conditional(a)
        norm_math = normalize_angle(a)
        print(
            f"Исходный: {a:>6.1f} | "
            f"Ветвление: {norm_cond:>6.1f} | "
            f"Формула: {norm_math:>6.1f}"
        )
