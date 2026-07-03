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


if __name__ == '__main__':
    # Импортируем matplotlib локально для тестов
    import matplotlib
    # Переключаем бэкенд на неинтерактивный, чтобы избежать падений при отсутствии X-сервера (GUI)
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    print("Запуск автономного тестирования модуля spectrum.py...")
    
    # 1. Генерируем синтетическую сетку времени (от 0 до 50 пс с шагом 0.05 пс)
    t = np.linspace(0, 50, 1000)
    
    # 2. Генерируем реалистичный ТГц импульс (затухающая синусоида + шум + DC смещение)
    t0 = 15.0  # Положение центра импульса
    w = 2.0    # Ширина импульса
    f0 = 1.2   # Центральная частота импульса (ТГц)
    
    # Сигнал фона (чистый воздух)
    E_bg_raw = np.exp(-0.5 * ((t - t0) / w) ** 2) * np.cos(2 * np.pi * f0 * (t - t0)) + 0.15
    # Сигнал образца (ослабленный и слегка зашумленный)
    E_sig_raw = 0.6 * np.exp(-0.5 * ((t - t0) / w) ** 2) * np.cos(2 * np.pi * f0 * (t - t0)) + 0.15
    
    # Добавим белый гауссов шум ко обоим сигналам
    np.random.seed(42)  # Фиксируем seed для воспроизводимости
    noise_bg = np.random.normal(0, 0.015, len(t))
    noise_sig = np.random.normal(0, 0.015, len(t))
    E_bg = E_bg_raw + noise_bg
    E_sig = E_sig_raw + noise_sig
    
    # 3. Тестируем удаление постоянного смещения и применение окна
    E_sig_dc = remove_dc(E_sig)
    E_sig_win, win = apply_gaussian_window(t, E_sig_dc)
    
    print("  - Среднее значение до удаления DC:", np.mean(E_sig))
    print("  - Среднее значение после удаления DC:", np.mean(E_sig_dc))
    print("  - Координата найденного центра пика:", t[find_peak_center(E_sig_dc)], "пс")
    
    # 4. Вычисляем сквозной конвейер пропускания
    freqs, spec_sig, spec_bg, transmission = calculate_transmission(t, E_sig, t, E_bg)
    
    # 5. Строим двухпанельный проверочный график для сигналов
    plt.figure(figsize=(10, 8))
    
    # Панель 1: Временной сигнал и Гауссово окно
    plt.subplot(2, 1, 1)
    plt.plot(t, E_sig, 'gray', alpha=0.5, label='Сырой сигнал образца')
    plt.plot(t, E_sig_dc, 'royalblue', label='Сигнал после удаления DC')
    plt.plot(t, win * np.max(E_sig_dc), 'crimson', linestyle='--', label='Гауссово окно (масштаб)')
    plt.plot(t, E_sig_win, 'darkblue', linewidth=1.5, label='Заокненный сигнал')
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
