import numpy as np
from scipy.fft import rfft, rfftfreq
import config

def remove_dc(E: np.ndarray) -> np.ndarray:
    """
    Удаляет постоянную составляющую (DC offset) из сигнала E,
    вычитая его среднее арифметическое значение.
    """
    return E - np.mean(E)


def find_peak_center(E: np.ndarray) -> int:
    """
    Находит индекс точки с максимальной по модулю амплитудой сигнала.
    Используется для точного центрирования временного окна на главном импульсе.
    """
    return int(np.argmax(np.abs(E)))


def apply_gaussian_window(t: np.ndarray, E: np.ndarray, sigma_ps: float = None, peak_idx: int = None) -> tuple[np.ndarray, np.ndarray]:
    """
    Создает Гауссово окно с заданной полушириной sigma_ps (в пикосекундах)
    вокруг временного пика сигнала и перемножает его с сигналом.
    
    Если параметр peak_idx не задан, положение пика находится автоматически 
    по максимуму абсолютного значения сигнала E с помощью find_peak_center.
    Если параметр sigma_ps не задан, используется стандартное значение из config.SIGMA_PS.
    """
    if sigma_ps is None:
        sigma_ps = config.SIGMA_PS
        
    if peak_idx is None:
        peak_idx = find_peak_center(E)
        
    t_peak = t[peak_idx]
    
    # Формула Гауссова распределения: exp(- (t - t_peak)^2 / (2 * sigma^2))
    window = np.exp(-0.5 * ((t - t_peak) / sigma_ps) ** 2)
    E_windowed = E * window
    
    return E_windowed, window


def compute_spectrum(t: np.ndarray, E: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Вычисляет спектр амплитуд ТГц-импульса.
    Возвращает ось частот (в ТГц) и вещественный амплитудный спектр.
    """
    N = len(E)
    dt = t[1] - t[0]  # Шаг временной сетки в пикосекундах
    
    # rfft вычисляет спектр только для вещественного сигнала E
    spectrum_complex = rfft(E)
    
    # Модуль комплексного числа дает амплитуду спектральной гармоники
    amplitude_spectrum = np.abs(spectrum_complex)
    
    # Генерируем шкалу частот в ТГц (так как dt задан в пикосекундах, f = 1/dt будет в ТГц)
    freqs = rfftfreq(N, d=dt)
    
    return freqs, amplitude_spectrum


def calculate_transmission(t_sig: np.ndarray, E_sig: np.ndarray, 
                           t_bg: np.ndarray, E_bg: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Полный цикл обработки: от сырого ТГц-сигнала до спектра пропускания по мощности."""
    
    # 1. Удаление постоянного смещения поля
    E_sig_clean = remove_dc(E_sig)
    E_bg_clean = remove_dc(E_bg)
    
    # Поиск центра пика по опорному сигналу (фона) как золотой стандарт
    peak_idx = find_peak_center(E_bg_clean)
    
    # 2. Наложение временного Гауссова окна (центрированного по пику опорного сигнала)
    E_sig_win, _ = apply_gaussian_window(t_sig, E_sig_clean, peak_idx=peak_idx)
    E_bg_win, _ = apply_gaussian_window(t_bg, E_bg_clean, peak_idx=peak_idx)
    
    # 3. Расчет БПФ
    freqs, spec_sig = compute_spectrum(t_sig, E_sig_win)
    _, spec_bg = compute_spectrum(t_bg, E_bg_win)
    
    # 4. Расчет пропускания по мощности (T = |E_sig / E_bg|^2)
    # Используем np.maximum для предотвращения деления на ноль на краях диапазона
    spec_bg_safe = np.maximum(spec_bg, 1e-10)
    transmission = (spec_sig / spec_bg_safe) ** 2
    
    return freqs, spec_sig, spec_bg, transmission


def process_dataset(data_store: dict) -> dict:
    """
    Выполняет пакетную обработку всей базы данных.
    Для каждой уникальной пары углов (angle1, angle2):
      1. Находит все повторения.
      2. Для каждого повторения рассчитывает спектр сигнала, спектр фона и пропускание.
      3. Усредняет спектр пропускания и спектр фона по всем повторениям для компенсации дрейфа.
      4. Сохраняет усредненные результаты в исходный словарь под новыми тегами:
         ('spec_avg', angle1, angle2, None) -> (freqs, transmission_avg)
         ('spec_bg_avg', angle1, angle2, None) -> (freqs, spec_bg_avg)
    """
    # Шаг 1. Найдем все уникальные пары углов (angle1, angle2) в сырых данных
    angle_pairs = set()
    for key in data_store.keys():
        if key[0] == 'signal_raw':
            angle_pairs.add((key[1], key[2]))
            
    # Шаг 2. Для каждой пары углов проводим обработку
    for angle1, angle2 in sorted(angle_pairs):
        transmissions = []
        bg_spectra = []
        freqs_common = None
        
        # Находим все повторения для данной пары углов
        reps = [key[3] for key in data_store.keys() 
                if key[0] == 'signal_raw' and key[1] == angle1 and key[2] == angle2]
                
        for rep in sorted(reps):
            sig_key = ('signal_raw', angle1, angle2, rep)
            bg_key = ('bg_raw', angle1, angle2, rep)
            
            if bg_key in data_store:
                t_sig, E_sig = data_store[sig_key]
                t_bg, E_bg = data_store[bg_key]
                
                # Рассчитываем пропускание для конкретной реплики
                freqs, spec_sig, spec_bg, transmission = calculate_transmission(
                    t_sig, E_sig, t_bg, E_bg
                )
                
                transmissions.append(transmission)
                bg_spectra.append(spec_bg)
                if freqs_common is None:
                    freqs_common = freqs
                    
        if transmissions:
            # Усредняем по всем повторениям (ось 0)
            trans_avg = np.mean(transmissions, axis=0)
            bg_avg = np.mean(bg_spectra, axis=0)
            
            # Сохраняем результаты в базу данных с Repetition = None
            data_store[('spec_avg', angle1, angle2, None)] = (freqs_common, trans_avg)
            data_store[('spec_bg_avg', angle1, angle2, None)] = (freqs_common, bg_avg)
            
    return data_store


if __name__ == '__main__':
    # Импортируем matplotlib локально для тестов
    import matplotlib
    # Переключаем бэкенд на неинтерактивный, чтобы избежать падений при отсутствии X-сервера (GUI)
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    print("Запуск автономного тестирования модуля spectrum.py на реальных данных...")
    
    import config
    from data_loader import load_tds_data
    from pathlib import Path
    
    # 1. Загружаем реальные экспериментальные данные
    t_sig, E_sig = load_tds_data(config.DATA_DIR / "50-0-1-bg_4.txt")
    t_bg, E_bg = load_tds_data(config.DATA_DIR / "bg_4.txt")
    
    # 2. Тестируем удаление постоянного смещения и применение окна
    E_sig_dc = remove_dc(E_sig)
    E_sig_win, win = apply_gaussian_window(t_sig, E_sig_dc)
    
    print("  - Среднее значение до удаления DC:", np.mean(E_sig))
    print("  - Среднее значение после удаления DC:", np.mean(E_sig_dc))
    print("  - Координата найденного центра пика:", t_sig[find_peak_center(E_sig_dc)], "пс")
    
    # 3. Вычисляем сквозной конвейер пропускания
    freqs, spec_sig, spec_bg, transmission = calculate_transmission(t_sig, E_sig, t_bg, E_bg)
    
    # 4. Строим двухпанельный проверочный график для сигналов
    plt.figure(figsize=(10, 8))
    
    # Панель 1: Временной сигнал и Гауссово окно
    plt.subplot(2, 1, 1)
    plt.plot(t_sig, E_sig, 'gray', alpha=0.5, label='Сырой сигнал образца')
    plt.plot(t_sig, E_sig_dc, 'royalblue', label='Сигнал после удаления DC')
    plt.plot(t_sig, win * np.max(E_sig_dc), 'crimson', linestyle='--', label='Гауссово окно (масштаб)')
    plt.plot(t_sig, E_sig_win, 'darkblue', linewidth=1.5, label='Заокненный сигнал')
    plt.title("Временная область: Наложение окна")
    plt.xlabel("Время (пс)")
    plt.ylabel("Амплитуда поля E (у.е.)")
    plt.grid(True, linestyle=':')
    plt.legend()
    
    # Панель 2: Спектры и пропускание
    plt.subplot(2, 1, 2)
    # Показываем спектр в пределах полезного ТГц диапазона
    mask = (freqs >= 0.1) & (freqs <= 3.0)
    plt.plot(freqs[mask], spec_bg[mask], 'crimson', label='Спектр фона (воздух)')
    plt.plot(freqs[mask], spec_sig[mask], 'royalblue', label='Спектр образца')
    plt.plot(freqs[mask], transmission[mask], 'darkgreen', linewidth=2, label='Пропускание по мощности T(v)')
    plt.title("Частотная область: Спектры и Пропускание по мощности")
    plt.xlabel("Частота (ТГц)")
    plt.ylabel("Амплитуда / Пропускание")
    plt.grid(True, linestyle=':')
    plt.legend()
    
    plt.tight_layout()
    output_png = "test_spectrum_dsp.png"
    plt.savefig(output_png, dpi=150)
    plt.close()
    
    print(f"Тестирование успешно завершено! График сохранен в файл: {output_png}")
