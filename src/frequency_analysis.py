import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import config
import data_loader
import spectrum
import theoretical

def analyze_polarizer_over_spectrum(freq_start=0.2, freq_end=1.8):
    """
    Выполняет автоматическую подгонку параметров решетки на каждой частоте
    в заданном диапазоне.
    """
    # 1. Загрузка и подготовка данных в словарь-хранилище
    data_store = data_loader.load_dataset_to_store(config.DATA_DIR)
    data_store = spectrum.process_dataset(data_store)
    
    # Извлекаем все ключи усредненных спектров пропускания
    spectra_keys = sorted([k for k in data_store.keys() if k[0] == 'spec_avg'])
    if not spectra_keys:
         raise ValueError("Не найдены усредненные спектры в хранилище данных!")
         
    angles = np.array([k[1] for k in spectra_keys])
    freqs = data_store[spectra_keys[0]][0]
    
    # Выбираем индексы частот в рабочем диапазоне
    target_indices = np.where((freqs >= freq_start) & (freqs <= freq_end))[0]
    analysis_freqs = freqs[target_indices]
    print(f"Найдено {len(target_indices)} частотных точек для анализа в диапазоне [{freq_start:.2f}, {freq_end:.2f}] ТГц.")
    
    # Резервируем массивы для результатов подгонки
    opt_p_arr = []
    opt_d_arr = []
    opt_scale_arr = []
    opt_loss_arr = []
    rmse_db_arr = []
    
    # Перебираем частоты
    for step_num, idx in enumerate(target_indices):
        f = freqs[idx]
        if step_num % 10 == 0 or step_num == len(target_indices) - 1:
            print(f"  Обработка: шаг {step_num + 1}/{len(target_indices)} (частота {f:.2f} ТГц)...")
        
        # Извлекаем экспериментальное пропускание на данной частоте
        exp_trans = []
        for k in spectra_keys:
            val = data_store[k][1][idx]
            exp_trans.append(val)
            
        exp_trans = np.array(exp_trans)
        exp_trans_db = 10 * np.log10(np.maximum(exp_trans, 1e-12))
        
        # Оптимизируемая функция (loss)
        def loss_func(params):
            p, d, ps, ls = params
            if d >= p * ps:
                return 1e6
            y_db = np.array([theoretical.transmission_db_modified(
                ang, p, d, f, ps, ls) for ang in angles])
            return np.sqrt(np.mean((exp_trans_db - y_db)**2))
        
        # Начальное приближение и границы
        initial_guess = [config.P_DEFAULT, config.D_DEFAULT, 
                         config.PERIOD_SCALE_DEFAULT, config.LOSS_FACTOR_DEFAULT]
        bounds = [(5e-6, 30e-6), (1e-6, 15e-6), (0.5, 2.0), (0.0, 5.0)]
        
        # Запуск оптимизации
        res = minimize(loss_func, initial_guess, method='Nelder-Mead', bounds=bounds, tol=1e-2)
        
        if res.success:
            opt_p_arr.append(res.x[0] * 1e6)      # в мкм
            opt_d_arr.append(res.x[1] * 1e6)      # в мкм
            opt_scale_arr.append(res.x[2])
            opt_loss_arr.append(res.x[3])
            rmse_db_arr.append(res.fun)
        else:
            # В случае неудачи записываем NaN
            opt_p_arr.append(np.nan)
            opt_d_arr.append(np.nan)
            opt_scale_arr.append(np.nan)
            opt_loss_arr.append(np.nan)
            rmse_db_arr.append(np.nan)
            
    return (analysis_freqs, np.array(opt_p_arr), np.array(opt_d_arr), 
            np.array(opt_scale_arr), np.array(opt_loss_arr), np.array(rmse_db_arr))

def plot_frequency_dependence(freqs, p_vals, d_vals, scale_vals, loss_vals, rmse_vals):
    """
    Строит графики зависимостей оптимальных геометрических и оптических 
    параметров поляризатора от частоты.
    """
    fig, axs = plt.subplots(5, 1, figsize=(10, 14), sharex=True)
    plt.subplots_adjust(hspace=0.25, top=0.95, bottom=0.05)
    fig.suptitle("Спектральная зависимость оптимизированных параметров поляризатора", fontsize=14)
    
    # 1. Шаг решетки P
    axs[0].plot(freqs, p_vals, 'b-o', markersize=4, label="Оптимизированный шаг")
    axs[0].axhline(config.P_DEFAULT*1e6, color='gray', linestyle='--', label="Паспортное значение")
    axs[0].set_ylabel("P (мкм)")
    axs[0].grid(True)
    axs[0].legend()
    
    # 2. Диаметр проволоки D
    axs[1].plot(freqs, d_vals, 'g-s', markersize=4, label="Оптимизированный диаметр")
    axs[1].axhline(config.D_DEFAULT*1e6, color='gray', linestyle='--', label="Паспортное значение")
    axs[1].set_ylabel("D (мкм)")
    axs[1].grid(True)
    axs[1].legend()
    
    # 3. Масштабный коэффициент периода Period Scale
    axs[2].plot(freqs, scale_vals, 'r-^', markersize=4)
    axs[2].axhline(1.0, color='gray', linestyle='--')
    axs[2].set_ylabel("Period Scale")
    axs[2].grid(True)
    
    # 4. Коэффициент потерь Loss Factor
    axs[3].plot(freqs, loss_vals, 'm-d', markersize=4)
    axs[3].set_ylabel("Loss (дБ/ТГц)")
    axs[3].grid(True)
    
    # 5. Качество подгонки RMSE
    axs[4].plot(freqs, rmse_vals, 'k-x', markersize=4)
    axs[4].set_ylabel("RMSE (дБ)")
    axs[4].set_xlabel("Частота (ТГц)")
    axs[4].grid(True)
    
    plt.show()

if __name__ == "__main__":
    # Настроим неинтерактивный бэкенд для автономного теста в песочнице
    import matplotlib
    matplotlib.use('Agg')
    
    print("Запуск тестирования модуля frequency_analysis.py...")
    try:
        results = analyze_polarizer_over_spectrum()
        print("Оптимизация по спектру завершена. Построение графиков...")
        plot_frequency_dependence(*results)
        print("Модуль протестирован успешно.")
    except Exception as e:
        print(f"Ошибка при тестировании модуля: {e}")
