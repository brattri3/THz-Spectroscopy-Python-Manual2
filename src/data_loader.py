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
    
    # Нормализуем углы поляризаторов с помощью готовой утилиты
    angle1 = normalize_angle(angle1)
    angle2 = normalize_angle(angle2)
        
    return angle1, angle2, repetition, bg_name


def load_tds_data(filepath):
    """
    Загружает временной ТГц сигнал из текстового файла.
    Возвращает два одномерных массива NumPy: время (t) и амплитуду (E).
    """
    t, E = np.loadtxt(filepath, unpack=True, usecols=(0, 1))
    return t, E


def load_dataset_to_store(data_dir) -> dict:
    """
    Сканирует папку data_dir, парсит файлы сигналов, находит парные фоновые файлы
    и загружает всё в единый словарь-хранилище data_store с составными ключами.
    """
    data_store = {}
    path = Path(data_dir)
    
    # Шаг 1. Предварительно загружаем все фоновые файлы по их именам в памяти
    bg_files = {}
    for filepath in path.glob("*.txt"):
        if filepath.name.startswith("bg"):
            bg_id = filepath.stem  # например, 'bg_1'
            t, E = load_tds_data(filepath)
            bg_files[bg_id] = (t, E)
            
    # Шаг 2. Сканируем сигнальные файлы образцов и привязываем их к фонам
    for filepath in path.glob("*.txt"):
        filename = filepath.name
        
        # Пропускаем фоны, их мы уже считали на Шаге 1
        if filename.startswith("bg"):
            continue
            
        try:
            angle1, angle2, rep, bg_name = parse_filename(filename)
        except ValueError:
            # Пропускаем файлы с некорректным или системным именем
            continue
            
        # Читаем данные сигнала образца
        t, E_signal = load_tds_data(filepath)
        
        # Сохраняем сырой сигнал образца в СУБД под составным ключом
        data_store[('signal_raw', angle1, angle2, rep)] = (t, E_signal)
        
        # Связываем этот проход с конкретным сырым фоном по его имени
        if bg_name in bg_files:
            t_bg, E_bg = bg_files[bg_name]
            # Записываем фоновый сигнал (background) с теми же углами и номером повторения!
            # Это гарантирует, что при обработке они составят неразрывную пару.
            data_store[('bg_raw', angle1, angle2, rep)] = (t_bg, E_bg)
            
    return data_store


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
