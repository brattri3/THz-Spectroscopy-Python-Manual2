import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons
from pathlib import Path
import config
import data_loader
import spectrum

def generate_synthetic_dataset(data_dir):
    """
    Генерирует синтетический набор данных ТГц спектроскопии для тестирования,
    если директория пуста или отсутствует.
    """
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    # Если в папке уже есть txt файлы, ничего не делаем
    if list(path.glob("*.txt")):
        return
        
    print(f"Директория {data_dir} пуста. Генерируем синтетический набор данных...")
    
    t = np.linspace(0, 50, 500)
    t0 = 15.0
    w = 2.0
    f0 = 1.2
    
    # Генерируем 3 файла фона (bg_1.txt, bg_2.txt, bg_3.txt)
    np.random.seed(42)
    for rep in [1, 2, 3]:
        # Опорный сигнал (воздух)
        E_bg = np.exp(-0.5 * ((t - t0) / w) ** 2) * np.cos(2 * np.pi * f0 * (t - t0))
        # Добавляем DC смещение и небольшой шум, зависящий от номера повторения (дрейф!)
        E_bg += 0.15 + np.random.normal(0, 0.01 + 0.005 * rep, len(t))
        
        filepath = path / f"bg_{rep}.txt"
        np.savetxt(filepath, np.column_stack((t, E_bg)))
        
    # Генерируем файлы сигналов образца для разных углов
    # Согласно закону Малюса для амплитуды ТГц поля: E_sample = E_bg * cos(angle)
    # Плюс учтем дрейф прибора
    angles = [0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0]
    for angle in angles:
        for rep in [1, 2, 3]:
            # Сигнал образца
            rad = np.radians(angle)
            factor = np.cos(rad)  # Физическое ослабление
            
            E_sig = factor * np.exp(-0.5 * ((t - t0) / w) ** 2) * np.cos(2 * np.pi * f0 * (t - t0))
            # Добавим DC и дрейфующий шум
            E_sig += 0.15 + np.random.normal(0, 0.01 + 0.005 * rep, len(t))
            
            # Формат имени: angle1-angle2-repetition-bg_name.txt
            filename = f"{angle:.1f}-0.0-{rep}-bg_{rep}.txt"
            filepath = path / filename
            np.savetxt(filepath, np.column_stack((t, E_sig)))
            
    print("Синтетический набор данных успешно создан.")


def main_interactive():
    # Гарантируем наличие данных
    generate_synthetic_dataset(config.DATA_DIR)
    
    # 1. Загружаем экспериментальный датасет в СУБД-хранилище
    data_store = data_loader.load_dataset_to_store(config.DATA_DIR)
    
    # 2. Выполняем пакетную обработку всей базы данных
    data_store = spectrum.process_dataset(data_store)
    
    # Получаем список уникальных углов для переключения
    # Фильтруем теги 'spec_avg' в базе данных
    spectra_keys = sorted([k for k in data_store.keys() if k[0] == 'spec_avg'])
    if not spectra_keys:
        print("Ошибка: обработанные спектры не найдены в базе данных!")
        return
        
    # Преобразуем ключи в строковые метки для виджета RadioButtons
    label_to_key = {f"Угол {k[1]}°": k for k in spectra_keys}
    labels = list(label_to_key.keys())
    
    initial_label = labels[0]
    initial_key = label_to_key[initial_label]
    angle1, angle2 = initial_key[1], initial_key[2]
    
    # 3. Подготавливаем фигуру и сетку графиков (Plot Grid)
    # Создаем вертикальную сетку из двух графиков (временной сигнал и спектр)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8))
    plt.subplots_adjust(left=0.25, hspace=0.35) # Оставляем место слева для панели радиокнопок
    
    # Получаем сырой временной сигнал (первое повторение для начального угла)
    rep_init = 1
    sig_key_init = ('signal_raw', angle1, angle2, rep_init)
    t_sig, E_sig = data_store[sig_key_init]
    
    # Очищаем от DC и накладываем окно
    E_sig_dc = spectrum.remove_dc(E_sig)
    E_sig_win, win = spectrum.apply_gaussian_window(t_sig, E_sig_dc)
    
    # Получаем спектр пропускания из СУБД для начального угла
    freqs, transmission = data_store[initial_key]
    
    # 4. Строим начальные линии на ax1 (временная область)
    line_raw, = ax1.plot(
        t_sig, E_sig_dc, color='gray', alpha=0.5, 
        label='Исходный сигнал (без DC)'
    )
    line_win, = ax1.plot(
        t_sig, E_sig_win, color='royalblue', linewidth=1.5, 
        label='Сигнал после окна'
    )
    # Показываем огибающую окна (масштабированную под максимум сигнала)
    max_amp = np.max(np.abs(E_sig_dc))
    line_envelope_pos, = ax1.plot(t_sig, win * max_amp, 'r--', alpha=0.7, label='Огибающая окна')
    line_envelope_neg, = ax1.plot(t_sig, -win * max_amp, 'r--', alpha=0.7)
    
    ax1.set_xlabel('Время задержки (пс)')
    ax1.set_ylabel('Амплитуда поля E (у.е.)')
    ax1.set_title(f'Временная область. Угол 1: {angle1}°')
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right', fontsize=9)
    
    # 5. Строим начальные линии на ax2 (частотная область)
    mask = (freqs >= config.F_MIN) & (freqs <= config.F_MAX)
    line_trans, = ax2.plot(
        freqs[mask], transmission[mask], color='darkgreen', linewidth=2,
        label=r'Пропускание $T(\nu)$'
    )
    ax2.set_xlabel('Частота (ТГц)')
    ax2.set_ylabel('Коэффициент пропускания по мощности')
    ax2.set_title(f'Частотная область (Пропускание). Угол 1: {angle1}°')
    ax2.set_xlim(config.F_MIN, config.F_MAX)
    ax2.set_ylim(-0.05, 1.1)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='lower left', fontsize=9)
    
    # 6. Создаем панель радиокнопок слева
    ax_radio = plt.axes([0.02, 0.3, 0.16, 0.4], facecolor='#f5f5f5')
    radio = RadioButtons(ax_radio, labels)
    
    # 7. Функция обратного вызова для мгновенного обновления данных в сетке
    def update_plot(label):
        key = label_to_key[label]
        a1, a2 = key[1], key[2]
        
        # Обновляем временные сигналы (берем реплику 1)
        sig_key = ('signal_raw', a1, a2, 1)
        if sig_key in data_store:
            t_new, E_new = data_store[sig_key]
            E_new_dc = spectrum.remove_dc(E_new)
            E_new_win, win_new = spectrum.apply_gaussian_window(t_new, E_new_dc)
            
            line_raw.set_xdata(t_new)
            line_raw.set_ydata(E_new_dc)
            line_win.set_xdata(t_new)
            line_win.set_ydata(E_new_win)
            
            # Обновляем огибающую окна
            max_amp_new = np.max(np.abs(E_new_dc))
            line_envelope_pos.set_xdata(t_new)
            line_envelope_pos.set_ydata(win_new * max_amp_new)
            line_envelope_neg.set_xdata(t_new)
            line_envelope_neg.set_ydata(-win_new * max_amp_new)
            
            ax1.set_title(f'Временная область. Угол 1: {a1}°')
            ax1.relim()
            ax1.autoscale_view(scalex=False, scaley=True)
            
        # Обновляем спектр пропускания
        freqs_new, trans_new = data_store[key]
        mask_new = (freqs_new >= config.F_MIN) & (freqs_new <= config.F_MAX)
        
        line_trans.set_xdata(freqs_new[mask_new])
        line_trans.set_ydata(trans_new[mask_new])
        
        ax2.set_title(f'Частотная область (Пропускание). Угол 1: {a1}°')
        ax2.relim()
        ax2.autoscale_view(scalex=False, scaley=True)
        
        # Обновляем фигуру
        fig.canvas.draw_idle()
        
    radio.on_clicked(update_plot)
    plt.show()


def plot_all_transmissions():
    # Загружаем данные и вычисляем спектры для всех углов
    data_store = data_loader.load_dataset_to_store(config.DATA_DIR)
    data_store = spectrum.process_dataset(data_store)
    
    spectra_keys = sorted([k for k in data_store.keys() if k[0] == 'spec_avg'])
    if not spectra_keys:
        print("Ошибка: обработанные спектры не найдены в базе данных!")
        return
        
    plt.figure(figsize=(10, 6))
    
    # Используем цветовую карту для красивого плавного градиента линий
    colors = plt.cm.plasma(np.linspace(0, 0.85, len(spectra_keys)))
    
    for key, color in zip(spectra_keys, colors):
        freqs, transmission = data_store[key]
        # Строим график только в полезном диапазоне частот
        mask = (freqs >= config.F_MIN) & (freqs <= config.F_MAX)
        plt.plot(freqs[mask], transmission[mask], label=f'Угол {key[1]}°', color=color, linewidth=1.5)
        
    plt.xlim(config.F_MIN, config.F_MAX)
    plt.ylim(-0.05, 1.1)
    plt.xlabel('Частота (ТГц)')
    plt.ylabel('Коэффициент пропускания')
    plt.title('Семейство спектров пропускания для различных углов поворота поляризатора')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='lower left', ncol=2) # выводим легенду в две колонки
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    # Переключим бэкенд на неинтерактивный для автономного теста при компиляции/линте
    import matplotlib
    matplotlib.use('Agg')
    
    print("Запуск тестирования interactive_plots.py...")
    # Проверим, что всё отрабатывает без графического окна (режим Agg)
    generate_synthetic_dataset(config.DATA_DIR)
    data_store = data_loader.load_dataset_to_store(config.DATA_DIR)
    data_store = spectrum.process_dataset(data_store)
    print("  - Загружено ключей в базу:", len(data_store))
    print("  - Спектральные ключи:", sorted([k for k in data_store.keys() if k[0] == 'spec_avg']))
    print("Тестирование завершено успешно.")
