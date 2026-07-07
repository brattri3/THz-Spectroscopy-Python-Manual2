import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons
from pathlib import Path
import config
import data_loader
import spectrum

def plot_time_signals(t_bg, E_bg, t_sig, E_sig):
    """
    Строит графики опорного сигнала (фона) и сигнала образца во временной области.
    """
    plt.figure(figsize=(9, 4.5))
    
    # Опорный сигнал (Фон)
    plt.plot(
        t_bg, E_bg, 
        color='crimson', 
        linestyle='--', 
        label='Опорный сигнал (Фон)', 
        alpha=0.8
    )
    
    # Сигнал образца
    plt.plot(
        t_sig, E_sig, 
        color='navy', 
        label='Сигнал образца', 
        alpha=0.9
    )
    
    plt.xlabel('Время задержки (пс)')
    plt.ylabel('Амплитуда поля E (у.е.)')
    plt.title('Сравнение ТГц импульсов: воздух vs образец')
    plt.grid(True, linestyle=':')
    plt.legend()
    plt.show()


def main_interactive():
    # Проверяем наличие файлов в директории данных
    path = Path(config.DATA_DIR)
    if not path.exists() or not list(path.glob("*.txt")):
        print(f"Ошибка: Директория данных '{config.DATA_DIR}' пуста или не существует!")
        print("Пожалуйста, распакуйте архив с экспериментальными данными.")
        return
    
    # Импортируем локально дополнительные инструменты для ЦОС и интерактивности
    from matplotlib.widgets import Slider
    from scipy.fft import rfft, rfftfreq
    
    # 1. Загружаем экспериментальный датасет в СУБД-хранилище
    data_store = data_loader.load_dataset_to_store(config.DATA_DIR)
    
    # Извлекаем метаданные: уникальные углы и повторения
    signal_keys = [k for k in data_store.keys() if k[0] == 'signal_raw']
    angles1 = sorted(list(set(k[1] for k in signal_keys)))
    reps = sorted(list(set(k[3] for k in signal_keys)))
    
    if not angles1 or not reps:
        print("Ошибка: необработанные данные не найдены в базе!")
        return
    
    # Начальное интерактивное состояние
    current_angle = angles1[0]
    current_rep = reps[0]
    current_sigma = 30.0
    
    # 3. Подготавливаем фигуру и сетку графиков (Plot Grid)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8))
    plt.subplots_adjust(left=0.25, bottom=0.15, hspace=0.35)
    
    # Вспомогательный метод для получения ключей по углу первого поляризатора и повторению
    def get_keys(angle, rep):
        sig_key = None
        bg_key = None
        for k in signal_keys:
            if k[1] == angle and k[3] == rep:
                sig_key = k
                bg_k = ('bg_raw', k[1], k[2], rep)
                if bg_k in data_store:
                    bg_key = bg_k
                break
        return sig_key, bg_key

    # Инициализационный расчет линий
    sig_k, bg_k = get_keys(current_angle, current_rep)
    t_sig, E_sig = data_store[sig_k]
    t_bg, E_bg = data_store[bg_k]
    
    E_sig_dc = E_sig - np.mean(E_sig)
    E_bg_dc = E_bg - np.mean(E_bg)
    peak_idx = np.argmax(np.abs(E_bg_dc))
    t_peak = t_bg[peak_idx]
    
    win = np.exp(-0.5 * ((t_sig - t_peak) / current_sigma) ** 2)
    E_sig_win = E_sig_dc * win
    
    win_bg = np.exp(-0.5 * ((t_bg - t_peak) / current_sigma) ** 2)
    E_bg_win = E_bg_dc * win_bg
    
    spec_sig = np.abs(rfft(E_sig_win))
    dt = t_sig[1] - t_sig[0]
    freqs = rfftfreq(len(E_sig_win), d=dt)
    spec_bg = np.abs(rfft(E_bg_win))
    spec_bg_safe = np.maximum(spec_bg, 1e-10)
    trans = (spec_sig / spec_bg_safe) ** 2
    
    # 4. Строим начальные линии на ax1 (временная область)
    line_raw, = ax1.plot(t_sig, E_sig_dc, color='gray', alpha=0.5, label='Исходный сигнал (без DC)')
    line_win, = ax1.plot(t_sig, E_sig_win, color='royalblue', linewidth=1.5, label='Сигнал после окна')
    max_amp = np.max(np.abs(E_sig_dc))
    line_envelope_pos, = ax1.plot(t_sig, win * max_amp, 'r--', alpha=0.7, label='Огибающая окна')
    line_envelope_neg, = ax1.plot(t_sig, -win * max_amp, 'r--', alpha=0.7)
    
    ax1.set_xlabel('Время задержки (пс)')
    ax1.set_ylabel('Амплитуда поля E (у.е.)')
    ax1.set_title(f'Временной ТГц-импульс (Угол {current_angle}°, Повторение {current_rep})')
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right', fontsize=9)
    
    # 5. Строим начальные линии на ax2 (частотная область)
    mask = (freqs >= config.F_MIN) & (freqs <= config.F_MAX)
    line_trans, = ax2.plot(freqs[mask], trans[mask], color='darkgreen', linewidth=2, label=r'Пропускание $T(\nu)$')
    ax2.set_xlabel('Частота (ТГц)')
    ax2.set_ylabel('Пропускание по мощности')
    ax2.set_title(f'Спектр пропускания (Угол {current_angle}°, Повторение {current_rep})')
    ax2.set_xlim(config.F_MIN, config.F_MAX)
    ax2.set_ylim(-0.05, 1.1)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='lower left', fontsize=9)
    
    # 6. Панели управления (Виджеты) слева
    ax_radio_angle = plt.axes([0.02, 0.5, 0.16, 0.35], facecolor='#f5f5f5')
    radio_angle = RadioButtons(ax_radio_angle, [f"Угол {a}°" for a in angles1])
    
    ax_radio_rep = plt.axes([0.02, 0.22, 0.16, 0.18], facecolor='#f5f5f5')
    radio_rep = RadioButtons(ax_radio_rep, [f"Повтор {r}" for r in reps])
    
    ax_slider_sigma = plt.axes([0.25, 0.05, 0.5, 0.03], facecolor='#f5f5f5')
    slider_sigma = Slider(ax_slider_sigma, 'Ширина окна (пс)', 5.0, 300.0, valinit=current_sigma, valstep=1.0)
    
    # 7. Функция обновления графиков
    def update(val):
        nonlocal current_angle, current_rep, current_sigma
        current_sigma = slider_sigma.val
        
        sig_k, bg_k = get_keys(current_angle, current_rep)
        if sig_k is None or bg_k is None:
            return
            
        t_s, E_s = data_store[sig_k]
        t_b, E_b = data_store[bg_k]
        
        E_s_dc = E_s - np.mean(E_s)
        E_b_dc = E_b - np.mean(E_b)
        p_idx = np.argmax(np.abs(E_b_dc))
        t_p = t_b[p_idx]
        
        w = np.exp(-0.5 * ((t_s - t_p) / current_sigma) ** 2)
        E_s_win = E_s_dc * w
        
        w_b = np.exp(-0.5 * ((t_b - t_p) / current_sigma) ** 2)
        E_b_win = E_b_dc * w_b
        
        spec_s = np.abs(rfft(E_s_win))
        d_t = t_s[1] - t_s[0]
        fr = rfftfreq(len(E_s_win), d=d_t)
        spec_b = np.abs(rfft(E_b_win))
        spec_b_s = np.maximum(spec_b, 1e-10)
        tr = (spec_s / spec_b_s) ** 2
        
        # Обновляем графики временного импульса
        line_raw.set_xdata(t_s)
        line_raw.set_ydata(E_s_dc)
        line_win.set_xdata(t_s)
        line_win.set_ydata(E_s_win)
        
        max_amp_new = np.max(np.abs(E_s_dc))
        line_envelope_pos.set_xdata(t_s)
        line_envelope_pos.set_ydata(w * max_amp_new)
        line_envelope_neg.set_xdata(t_s)
        line_envelope_neg.set_ydata(-w * max_amp_new)
        
        ax1.set_title(f'Временной ТГц-импульс (Угол {current_angle}°, Повторение {current_rep})')
        ax1.relim()
        ax1.autoscale_view(scalex=False, scaley=True)
        
        # Обновляем графики спектров пропускания
        mask_new = (fr >= config.F_MIN) & (fr <= config.F_MAX)
        line_trans.set_xdata(fr[mask_new])
        line_trans.set_ydata(tr[mask_new])
        
        ax2.set_title(f'Спектр пропускания (Угол {current_angle}°, Повторение {current_rep})')
        ax2.relim()
        ax2.autoscale_view(scalex=False, scaley=True)
        
        fig.canvas.draw_idle()
        
    def on_angle_changed(label):
        nonlocal current_angle
        current_angle = int(label.replace("Угол ", "").replace("°", ""))
        update(None)
        
    def on_rep_changed(label):
        nonlocal current_rep
        current_rep = int(label.replace("Повтор ", ""))
        update(None)
        
    radio_angle.on_clicked(on_angle_changed)
    radio_rep.on_clicked(on_rep_changed)
    slider_sigma.on_changed(update)
    
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


def plot_polarizer_theory_characteristics(p=config.P_DEFAULT, d=config.D_DEFAULT):
    """
    Строит теоретические спектры пропускания по амплитуде для перпендикулярной
    и параллельной составляющих поляризатора в диапазоне от 0.1 до 100 ТГц.
    """
    import theoretical
    
    # Задаем массив частот на логарифмической шкале от 0.1 до 100 ТГц
    freqs_THz = np.logspace(-1, 2, 500)
    c_light = 3e8
    
    t_perp_amps = []
    t_par_amps = []
    
    for f in freqs_THz:
        lambda_m = c_light / (f * 1e12)
        p_over_lambda = p / lambda_m
        d_over_p = d / p
        
        t_perp = theoretical.compute_t_perp(p_over_lambda, d_over_p)
        t_par = theoretical.compute_t_par(p_over_lambda, d_over_p)
        
        t_perp_amps.append(np.abs(t_perp))
        t_par_amps.append(np.abs(t_par))
        
    plt.figure(figsize=(10, 5))
    plt.semilogx(freqs_THz, t_perp_amps, color='royalblue', label=r'Перпендикулярная составляющая $|t_\perp|$', linewidth=2)
    plt.semilogx(freqs_THz, t_par_amps, color='crimson', label=r'Параллельная составляющая $|t_\parallel|$', linewidth=2)
    
    # Отмечаем резонансную частоту (Wood's anomaly) при lambda = p
    f_res = (c_light / p) / 1e12
    plt.axvline(f_res, color='orange', linestyle='--', label=f'Аномалия Вуда ({f_res:.1f} ТГц)')
    
    plt.xlim(0.1, 100)
    plt.ylim(-0.05, 1.15)
    plt.xlabel('Частота (ТГц)')
    plt.ylabel('Амплитудный коэффициент пропускания')
    plt.title(f'Спектры пропускания поляризатора ($p={p*1e6:.1f}$ мкм, $d={d*1e6:.1f}$ мкм)')
    plt.grid(True, which="both", linestyle=':', alpha=0.5)
    plt.legend(loc='center left')
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    # Переключим бэкенд на неинтерактивный для автономного теста при компиляции/линте
    import matplotlib
    matplotlib.use('Agg')
    
    print("Запуск тестирования plots.py...")
    path = Path(config.DATA_DIR)
    if not path.exists() or not list(path.glob("*.txt")):
        print("Ошибка: Тестовые данные отсутствуют. Пропуск тестирования.")
    else:
        data_store = data_loader.load_dataset_to_store(config.DATA_DIR)
        data_store = spectrum.process_dataset(data_store)
        print("  - Загружено ключей в базу:", len(data_store))
        print("  - Спектральные ключи:", sorted([k for k in data_store.keys() if k[0] == 'spec_avg']))
        
        # Проверяем работу новой теоретической функции
        print("  - Расчет теоретических спектров...")
        plot_polarizer_theory_characteristics()
    print("Тестирование завершено успешно.")
