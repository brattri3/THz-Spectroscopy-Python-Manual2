import numpy as np
from scipy.optimize import minimize
import config
import data_loader
import spectrum
import theoretical
import plots
import frequency_analysis

def run_single_frequency_fit(target_freq=0.5):
    """ Выполняет локальную численную оптимизацию на фиксированной частоте. """
    print(f"\n--- Шаг 3. Локальная оптимизация на частоте {target_freq} ТГц ---")
    
    # 1. Загрузка и подготовка экспериментальных данных
    data_store = data_loader.load_dataset_to_store(config.DATA_DIR)
    data_store = spectrum.process_dataset(data_store)
    
    # 2. Выборка спектров пропускания для всех углов
    spectra_keys = sorted([k for k in data_store.keys() if k[0] == 'spec_avg'])
    angles = np.array([k[1] for k in spectra_keys])
    
    freqs = data_store[spectra_keys[0]][0]
    idx = np.argmin(np.abs(freqs - target_freq))
    
    exp_trans = []
    for k in spectra_keys:
        val = data_store[k][1][idx]
        exp_trans.append(val)
    exp_trans = np.array(exp_trans)
    
    # Перевод пропускания в децибелы для оптимизации
    exp_trans_db = 10 * np.log10(np.maximum(exp_trans, 1e-12))
    
    # 3. Определение целевой функции потерь (RMSE)
    def loss_func(params):
        p, d, ps, ls = params
        if d >= p * ps:
            return 1e6
        y_db = np.array([theoretical.transmission_db_modified(
            ang, p, d, target_freq, ps, ls) for ang in angles])
        return np.sqrt(np.mean((exp_trans_db - y_db)**2))
        
    initial_guess = [config.P_DEFAULT, config.D_DEFAULT, 
                     config.PERIOD_SCALE_DEFAULT, config.LOSS_FACTOR_DEFAULT]
    bounds = [(5e-6, 30e-6), (1e-6, 15e-6), (0.5, 2.0), (0.0, 5.0)]
    
    # 4. Запуск оптимизатора Нелдера-Мида
    print("Запуск оптимизации Nelder-Mead...")
    res = minimize(loss_func, initial_guess, method='Nelder-Mead', bounds=bounds, tol=1e-2)
    
    if res.success:
        opt_p, opt_d, opt_scale, opt_loss = res.x
        print("Оптимизация успешно завершена!")
        print(f"  Оптимальный шаг P:       {opt_p*1e6:.2f} мкм (паспортный: {config.P_DEFAULT*1e6:.1f} мкм)")
        print(f"  Оптимальный диаметр D:   {opt_d*1e6:.2f} мкм (паспортный: {config.D_DEFAULT*1e6:.1f} мкм)")
        print(f"  Масштаб периода:         {opt_scale:.3f}")
        print(f"  Коэффициент потерь:      {opt_loss:.3f} дБ/ТГц")
        print(f"  Минимальное RMSE:        {res.fun:.4f} дБ")
    else:
        print("Ошибка оптимизации:", res.message)

def main():
    print("=========================================================")
    print("ОРКЕСТРАТОР ОБРАБОТКИ ДАННЫХ ТГЦ-СПЕКТРОСКОПИИ (main.py)")
    print("=========================================================")
    
    # Шаг 1. Интерактивная фильтрация и спектры сигналов
    print("\n--- Шаг 1. Интерактивный анализ временных сигналов и спектров ---")
    print("Закройте окно графика, чтобы перейти к следующему шагу...")
    plots.main_interactive()
    
    # Шаг 2. Построение семейства спектров пропускания для всех углов
    print("\n--- Шаг 2. Визуализация семейства спектров пропускания ---")
    print("Закройте окно графика, чтобы перейти к следующему шагу...")
    plots.plot_all_transmissions()
    
    # Шаг 3. Локальная численная оптимизация на фиксированной частоте
    run_single_frequency_fit(target_freq=0.5)
    
    # Шаг 4. Теоретические характеристики поляризатора по модели Бланко
    print("\n--- Шаг 4. Теоретический расчет коэффициентов пропускания ---")
    print("Закройте окно графика, чтобы перейти к следующему шагу...")
    plots.plot_polarizer_theory_characteristics()
    
    # Шаг 5. Пакетная оптимизация по всему спектру частот
    print("\n--- Шаг 5. Пакетная оптимизация геометрических параметров по спектру ---")
    print("Запуск численного анализа. Пожалуйста, подождите...")
    results = frequency_analysis.analyze_polarizer_over_spectrum()
    print("Построение финального дашборда результатов...")
    frequency_analysis.plot_frequency_dependence(*results)
    
    print("\nВсе этапы обработки ТГц данных успешно завершены!")

if __name__ == '__main__':
    # Настроим неинтерактивный бэкенд для тестов в песочнице
    import sys
    if '--test' in sys.argv or 'test' in sys.argv:
        import matplotlib
        matplotlib.use('Agg')
    main()
