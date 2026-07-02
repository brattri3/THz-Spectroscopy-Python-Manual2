from pathlib import Path
import numpy as np
from utils import normalize_angle

def parse_filename(filename: str):
    """
    Извлекает параметры эксперимента из имени файла.
    Ожидаемый формат: 'angle1-angle2-repetition-bg_name.txt'
    """
    # Убираем расширение (.txt)
    name_without_ext = Path(filename).stem 
    
    # Разбиваем строку по дефису
    parts = name_without_ext.split('-')
    
    # Проверяем, что в имени именно 4 части
    if len(parts) != 4:
        raise ValueError(f"Неизвестный формат файла: {filename}")
        
    angle1 = float(parts[0])
    angle2 = float(parts[1])
    repetition = int(parts[2])
    bg_name = parts[3]
    
    # Нормализуем угол первого ротатора с помощью готовой утилиты из Раздела 2
    angle1 = normalize_angle(angle1)
        
    return angle1, angle2, repetition, bg_name


def load_tds_data(filepath):
    """
    Загружает временной ТГц сигнал из текстового файла.
    Возвращает два одномерных массива NumPy: время (t) и амплитуду (E).
    """
    # unpack=True распаковывает колонки таблицы сразу в разные переменные.
    # usecols=(0, 1) указывает NumPy читать только первые две колонки,
    # полностью игнорируя третью колонку с позицией линии задержки.
    t, E = np.loadtxt(filepath, unpack=True, usecols=(0, 1))
    return t, E


if __name__ == "__main__":
    # Быстрый тест работоспособности функций модуля
    print("Тестирование функций модуля data_loader.py:")
    test_name = "10-0-1-bg_1.txt"
    try:
        a1, a2, rep, bg = parse_filename(test_name)
        print(f"Успешный парсинг имени '{test_name}':")
        print(f"  Угол 1 = {a1}°, Угол 2 = {a2}°, Повторение = {rep}, Имя фона = '{bg}'")
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
