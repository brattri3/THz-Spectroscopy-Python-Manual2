import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
from scipy.optimize import minimize
from scipy.fft import rfft, rfftfreq

import config
import data_loader
import spectrum
import theoretical

def load_first_repetition_dataset(data_dir):
    """ Загружает сырые сигналы первой реплики (Repetition = 1) образца и фона. """
    data_store = data_loader.load_dataset_to_store(data_dir)
    signals_raw = {}
    backgrounds = {}
    
    for key, val in data_store.items():
        if key[3] == 1:
            ang_pair = (key[1], key[2])
            if key[0] == 'signal_raw':
                signals_raw[ang_pair] = val
                # Привязываем фоновый сигнал с тем же Repetition
                bg_key = ('bg_raw', key[1], key[2], 1)
                if bg_key in data_store:
                    backgrounds[ang_pair] = data_store[bg_key]
                    
    return signals_raw, backgrounds

def load_and_average_dataset(data_dir):
    """ Загружает все реплики сигналов и усредняет их во временной области. """
    data_store = data_loader.load_dataset_to_store(data_dir)
    
    angle_pairs = set()
    for key in data_store.keys():
        if key[0] == 'signal_raw':
            angle_pairs.add((key[1], key[2]))
            
    signals_avg = {}
    backgrounds_avg = {}
    
    for angle1, angle2 in angle_pairs:
        ang_pair = (angle1, angle2)
        
        # Сбор и усреднение сигналов образца
        sig_measurements = []
        t_sig_common = None
        for key, val in data_store.items():
            if key[0] == 'signal_raw' and key[1] == angle1 and key[2] == angle2:
                t_sig, E_sig = val
                sig_measurements.append(E_sig)
                if t_sig_common is None:
                    t_sig_common = t_sig
                    
        # Сбор и усреднение сигналов фона
        bg_measurements = []
        t_bg_common = None
        for key, val in data_store.items():
            if key[0] == 'bg_raw' and key[1] == angle1 and key[2] == angle2:
                t_bg, E_bg = val
                bg_measurements.append(E_bg)
                if t_bg_common is None:
                    t_bg_common = t_bg
                    
        if sig_measurements:
            signals_avg[ang_pair] = (t_sig_common, np.mean(sig_measurements, axis=0))
        if bg_measurements:
            backgrounds_avg[ang_pair] = (t_bg_common, np.mean(bg_measurements, axis=0))
            
    return signals_avg, backgrounds_avg

def get_experimental_transmission_at_freq(spectra, target_freq):
    """ Извлекает экспериментальную угловую зависимость пропускания для заданной частоты. """
    raw_keys = sorted(list(spectra.keys()))
    angles = np.array([k[0] for k in raw_keys])
    
    freqs = spectra[raw_keys[0]][0]
    freq_idx = np.argmin(np.abs(freqs - target_freq))
    
    transmission_pow = []
    for k in raw_keys:
        trans = spectra[k][1][freq_idx]
        transmission_pow.append(trans)
        
    return angles, np.array(transmission_pow)

def compute_spectra_with_params(signals, backgrounds, pad_factor, sigma):
    """ Рассчитывает спектры пропускания при заданных Pad Factor и полуширине окна. """
    spectra = {}
    for angle_pair, (t_sig, E_sig) in signals.items():
        if angle_pair in backgrounds:
            t_bg, E_bg = backgrounds[angle_pair]
        else:
            bg_key = list(backgrounds.keys())[0]
            t_bg, E_bg = backgrounds[bg_key]
            
        E_sig_dc = E_sig - np.mean(E_sig)
        E_bg_dc = E_bg - np.mean(E_bg)
        
        peak_idx = np.argmax(np.abs(E_bg_dc))
        t_peak = t_bg[peak_idx]
        
        win_sig = np.exp(-0.5 * ((t_sig - t_peak) / sigma) ** 2)
        E_sig_win = E_sig_dc * win_sig
        
        win_bg = np.exp(-0.5 * ((t_bg - t_peak) / sigma) ** 2)
        E_bg_win = E_bg_dc * win_bg
        
        N_sig_padded = len(E_sig_win) * int(pad_factor)
        dt = t_sig[1] - t_sig[0]
        spec_sig = np.abs(rfft(E_sig_win, n=N_sig_padded))
        freqs = rfftfreq(N_sig_padded, d=dt)
        
        N_bg_padded = len(E_bg_win) * int(pad_factor)
        spec_bg = np.abs(rfft(E_bg_win, n=N_bg_padded))
        
        spec_bg_safe = np.maximum(spec_bg, 1e-10)
        trans = (spec_sig / spec_bg_safe) ** 2
        spectra[angle_pair] = (freqs, trans)
        
    return spectra

def run_step1_time_domain(signals_raw, backgrounds):
    print("\n--- Шаг 1: Интерактивная фильтрация во временной области ---")
    sorted_keys = sorted(list(signals_raw.keys()))
    label_to_key = {str(k): k for k in sorted_keys}
    labels = list(label_to_key.keys())
    
    sigma_init = 30.0
    current_key = sorted_keys[0]
    
    t_bg, E_bg = backgrounds[current_key]
    E_bg_dc = E_bg - np.mean(E_bg)
    peak_idx_bg = np.argmax(np.abs(E_bg_dc))
    t_peak = t_bg[peak_idx_bg]
    
    fig, (ax, ax_fft) = plt.subplots(2, 1, figsize=(11, 8))
    plt.subplots_adjust(left=0.25, bottom=0.15, hspace=0.35)
    
    t_sig, E_sig = signals_raw[current_key]
    E_sig_dc = E_sig - np.mean(E_sig)
    
    line_raw, = ax.plot(t_sig, E_sig_dc, color='gray', alpha=0.5, label='Исходный сигнал (реплика 1, без DC)')
    
    def get_windowed(t, E, sigma):
        win = np.exp(-0.5 * ((t - t_peak) / sigma) ** 2)
        return E * win, win
        
    E_win, win = get_windowed(t_sig, E_sig_dc, sigma_init)
    line_win, = ax.plot(t_sig, E_win, color='blue', linewidth=1.5, label='После окна')
    line_env, = ax.plot(t_sig, win * np.max(np.abs(E_sig_dc)), 'r--', alpha=0.7, label='Окно (масштаб)')
    
    ax.set_xlabel('Время задержки (пс)')
    ax.set_ylabel('Амплитуда (у.е.)')
    ax.set_title(f'Временной сигнал. Угол: {current_key[0]}°')
    ax.grid(True)
    ax.legend(loc='upper right')
    
    N = len(E_sig_dc)
    dt = t_sig[1] - t_sig[0]
    freqs_sig = rfftfreq(N, d=dt)
    spec_raw = np.abs(rfft(E_sig_dc))
    spec_win = np.abs(rfft(E_win))
    
    line_fft_raw, = ax_fft.plot(freqs_sig, spec_raw, color='gray', alpha=0.5, label='Спектр исходного сигнала')
    line_fft_win, = ax_fft.plot(freqs_sig, spec_win, color='blue', linewidth=1.5, label='Спектр после окна')
    
    ax_fft.set_xlabel('Частота (ТГц)')
    ax_fft.set_ylabel('Амплитуда (у.е.)')
    ax_fft.set_xlim(0, 3.0)
    ax_fft.set_title('Влияние окна на спектр БПФ')
    ax_fft.grid(True)
    ax_fft.legend(loc='upper right')
    
    ax_radio = plt.axes([0.02, 0.35, 0.16, 0.35], facecolor='#f0f0f0')
    radio = RadioButtons(ax_radio, labels)
    
    ax_sigma = plt.axes([0.30, 0.05, 0.45, 0.03])
    slider_sigma = Slider(ax_sigma, 'Ширина окна σ (пс)', 5.0, 500.0, valinit=sigma_init)
    
    ax_next = plt.axes([0.83, 0.04, 0.12, 0.06])
    btn_next = Button(ax_next, 'Далее ➔', color='lightblue', hovercolor='skyblue')
    
    result = {'sigma': sigma_init}
    
    def update(val):
        sigma = slider_sigma.val
        result['sigma'] = sigma
        
        key = label_to_key[radio.value_selected]
        t, E = signals_raw[key]
        E_dc = E - np.mean(E)
        
        t_b, E_b = backgrounds[key]
        E_b_dc = E_b - np.mean(E_b)
        p_idx_b = np.argmax(np.abs(E_b_dc))
        t_p_bg = t_b[p_idx_b]
        
        win_sig = np.exp(-0.5 * ((t - t_p_bg) / sigma) ** 2)
        E_w = E_dc * win_sig
        
        line_raw.set_ydata(E_dc)
        line_win.set_ydata(E_w)
        line_env.set_ydata(win_sig * np.max(np.abs(E_dc)))
        
        s_raw = np.abs(rfft(E_dc))
        s_win = np.abs(rfft(E_w))
        line_fft_raw.set_ydata(s_raw)
        line_fft_win.set_ydata(s_win)
        
        ax.set_title(f'Временной сигнал. Угол: {key[0]}°')
        ax.relim()
        ax.autoscale_view(scalex=False, scaley=True)
        ax_fft.relim()
        ax_fft.autoscale_view(scalex=False, scaley=True)
        fig.canvas.draw_idle()
        
    def on_radio_clicked(label):
        update(0)
        
    radio.on_clicked(on_radio_clicked)
    slider_sigma.on_changed(update)
    
    def next_callback(event):
        plt.close(fig)
        
    btn_next.on_clicked(next_callback)
    plt.show()
    return result

def run_step2_frequency_domain(signals, backgrounds, win_params):
    print("\n--- Шаг 2: Анализ спектров пропускания для всех углов ---")
    sigma = win_params['sigma']
    pad_init = config.PAD_FACTOR
    
    fig, (ax_pct, ax_db) = plt.subplots(1, 2, figsize=(12, 6))
    plt.subplots_adjust(bottom=0.22, left=0.08, right=0.95, wspace=0.25)
    
    sorted_keys = sorted(list(signals.keys()))
    
    def compute_all_transmissions(pad):
        all_trans = {}
        for key in sorted_keys:
            t_sig, E_sig = signals[key]
            t_bg, E_bg = backgrounds[key]
            
            E_sig_dc = E_sig - np.mean(E_sig)
            E_bg_dc = E_bg - np.mean(E_bg)
            
            peak_idx_bg = np.argmax(np.abs(E_bg_dc))
            t_peak = t_bg[peak_idx_bg]
            
            win_sig = np.exp(-0.5 * ((t_sig - t_peak) / sigma) ** 2)
            E_sig_win = E_sig_dc * win_sig
            
            win_bg = np.exp(-0.5 * ((t_bg - t_peak) / sigma) ** 2)
            E_bg_win = E_bg_dc * win_bg
            
            N_sig_padded = len(E_sig_win) * int(pad)
            dt = t_sig[1] - t_sig[0]
            spec_sig = np.abs(rfft(E_sig_win, n=N_sig_padded))
            freqs = rfftfreq(N_sig_padded, d=dt)
            
            N_bg_padded = len(E_bg_win) * int(pad)
            spec_bg = np.abs(rfft(E_bg_win, n=N_bg_padded))
            
            spec_bg_safe = np.maximum(spec_bg, 1e-10)
            trans = (spec_sig / spec_bg_safe) ** 2
            all_trans[key[0]] = (freqs, trans)
        return all_trans

    all_trans = compute_all_transmissions(pad_init)
    colors = plt.cm.plasma(np.linspace(0, 0.85, len(sorted_keys)))
    
    lines_pct = []
    lines_db = []
    
    for (ang_key, (freqs, trans)), color in zip(all_trans.items(), colors):
        mask = (freqs >= config.F_MIN) & (freqs <= config.F_MAX)
        l_pct, = ax_pct.plot(freqs[mask], trans[mask] * 100, label=f'{ang_key}°', color=color, linewidth=1.5)
        l_db, = ax_db.plot(freqs[mask], 10 * np.log10(np.maximum(trans[mask], 1e-12)), label=f'{ang_key}°', color=color, linewidth=1.5)
        lines_pct.append(l_pct)
        lines_db.append(l_db)
        
    ax_pct.set_xlabel('Частота (ТГц)')
    ax_pct.set_ylabel('Пропускание по мощности (%)')
    ax_pct.set_title('Пропускание в процентах')
    ax_pct.set_xlim(config.F_MIN, config.F_MAX)
    ax_pct.set_ylim(-5, 105)
    ax_pct.grid(True, linestyle='--', alpha=0.7)
    ax_pct.legend(loc='lower left', ncol=2, fontsize='small')
    
    ax_db.set_xlabel('Частота (ТГц)')
    ax_db.set_ylabel('Пропускание по мощности (дБ)')
    ax_db.set_title('Пропускание в децибелах')
    ax_db.set_xlim(config.F_MIN, config.F_MAX)
    ax_db.set_ylim(-60, 5)
    ax_db.grid(True, linestyle='--', alpha=0.7)
    ax_db.legend(loc='lower left', ncol=2, fontsize='small')
    
    ax_pad = plt.axes([0.25, 0.08, 0.45, 0.03])
    slider_pad = Slider(ax_pad, 'Pad Factor', 1, 8, valinit=pad_init, valstep=1)
    
    ax_next = plt.axes([0.83, 0.06, 0.12, 0.06])
    btn_next = Button(ax_next, 'Далее ➔', color='lightblue', hovercolor='skyblue')
    
    result = {'pad_factor': pad_init, 'sigma': sigma}
    
    def update(val):
        pad = int(slider_pad.val)
        result['pad_factor'] = pad
        new_all_trans = compute_all_transmissions(pad)
        
        for i, ang_key in enumerate(sorted(new_all_trans.keys())):
            fr, tr = new_all_trans[ang_key]
            mask = (fr >= config.F_MIN) & (fr <= config.F_MAX)
            lines_pct[i].set_xdata(fr[mask])
            lines_pct[i].set_ydata(tr[mask] * 100)
            lines_db[i].set_xdata(fr[mask])
            lines_db[i].set_ydata(10 * np.log10(np.maximum(tr[mask], 1e-12)))
            
        ax_pct.relim()
        ax_pct.autoscale_view(scalex=False, scaley=True)
        ax_db.relim()
        ax_db.autoscale_view(scalex=False, scaley=True)
        fig.canvas.draw_idle()
        
    slider_pad.on_changed(update)
    
    def next_callback(event):
        plt.close(fig)
        
    btn_next.on_clicked(next_callback)
    plt.show()
    return result

def run_step3_interactive_fit(spectra, pad_factor):
    print("\n--- Шаг 3: Сопоставление с теорией на фиксированной частоте ---")
    target_freq_init = 0.5
    
    exp_angles, exp_trans = get_experimental_transmission_at_freq(spectra, target_freq_init)
    exp_trans_db = 10 * np.log10(np.maximum(exp_trans, 1e-12))
    
    theta_range = np.linspace(-90, 90, 200)
    
    p_init = config.P_DEFAULT
    d_init = config.D_DEFAULT
    p_scale_init = config.PERIOD_SCALE_DEFAULT
    loss_init = config.LOSS_FACTOR_DEFAULT
    offset_init = 0.0
    
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1], hspace=0.25, wspace=0.25)
    
    ax_lin = fig.add_subplot(gs[0, 0])
    ax_res_lin = fig.add_subplot(gs[1, 0], sharex=ax_lin)
    ax_db = fig.add_subplot(gs[0, 1])
    ax_res_db = fig.add_subplot(gs[1, 1], sharex=ax_db)
    
    plt.subplots_adjust(bottom=0.38, left=0.08, right=0.95, top=0.90)
    
    scat_lin, = ax_lin.plot(exp_angles, exp_trans, 'ko', label="Эксперимент")
    scat_db, = ax_db.plot(exp_angles, exp_trans_db, 'ko', label="Эксперимент")
    
    line_lin, = ax_lin.plot(theta_range, np.zeros_like(theta_range), 'b-', label="Теория")
    line_db, = ax_db.plot(theta_range, np.zeros_like(theta_range), 'b-', label="Теория")
    
    bars_lin = ax_res_lin.bar(exp_angles, np.zeros_like(exp_angles), width=2.0, color='red', alpha=0.7, label="Остатки")
    bars_db = ax_res_db.bar(exp_angles, np.zeros_like(exp_angles), width=2.0, color='red', alpha=0.7, label="Остатки")
    
    ax_lin.set_ylabel('Пропускание (Отн. ед.)')
    ax_lin.set_ylim(-0.05, 1.05)
    ax_lin.grid(True)
    ax_lin.legend(loc='upper right')
    
    ax_res_lin.set_xlabel('Угол (градусы)')
    ax_res_lin.set_ylabel('Остатки (%)')
    ax_res_lin.set_ylim(-15, 15)
    ax_res_lin.grid(True)
    
    ax_db.set_ylabel('Пропускание (дБ)')
    ax_db.set_ylim(-40, 5)
    ax_db.grid(True)
    ax_db.legend(loc='lower left')
    
    ax_res_db.set_xlabel('Угол (градусы)')
    ax_res_db.set_ylabel('Остатки (дБ)')
    ax_res_db.set_ylim(-6, 6)
    ax_res_db.grid(True)
    
    ax_f  = plt.axes([0.15, 0.26, 0.50, 0.025])
    ax_p  = plt.axes([0.15, 0.21, 0.50, 0.025])
    ax_d  = plt.axes([0.15, 0.16, 0.50, 0.025])
    ax_ps = plt.axes([0.15, 0.11, 0.50, 0.025])
    ax_ls = plt.axes([0.15, 0.06, 0.50, 0.025])
    ax_offset = plt.axes([0.15, 0.01, 0.50, 0.025])
    
    raw_keys = list(spectra.keys())
    freqs_all = spectra[raw_keys[0]][0]
    f_min, f_max = freqs_all[0], freqs_all[-1]
    
    slider_f  = Slider(ax_f, 'Частота (ТГц)', f_min, f_max, valinit=target_freq_init, valstep=0.01)
    slider_p  = Slider(ax_p, 'P (мкм)', 5.0, 30.0, valinit=p_init*1e6)
    slider_d  = Slider(ax_d, 'D (мкм)', 1.0, 15.0, valinit=d_init*1e6)
    slider_ps = Slider(ax_ps, 'P Scale', 0.5, 2.0, valinit=p_scale_init)
    slider_ls = Slider(ax_ls, 'Loss', 0.0, 5.0, valinit=loss_init)
    slider_offset = Slider(ax_offset, 'Смещение угла (°)', -15.0, 15.0, valinit=offset_init)
    
    result = {
        'p': p_init,
        'd': d_init,
        'period_scale': p_scale_init,
        'loss_factor': loss_init,
        'theta_offset': offset_init,
        'last_freq': target_freq_init
    }
    
    def update(val):
        target_freq = slider_f.val
        p_val = slider_p.val * 1e-6
        d_val = slider_d.val * 1e-6
        ps_val = slider_ps.val
        ls_val = slider_ls.val
        offset_val = slider_offset.val
        
        result['p'] = p_val
        result['d'] = d_val
        result['period_scale'] = ps_val
        result['loss_factor'] = ls_val
        result['theta_offset'] = offset_val
        result['last_freq'] = target_freq
        
        exp_ang_f, exp_trans_f = get_experimental_transmission_at_freq(spectra, target_freq)
        exp_trans_db_f = 10 * np.log10(np.maximum(exp_trans_f, 1e-12))
        
        scat_lin.set_ydata(exp_trans_f)
        scat_db.set_ydata(exp_trans_db_f)
        
        y_db_dense = np.array([theoretical.transmission_db_modified(
            ang - offset_val, p_val, d_val, target_freq, ps_val, ls_val) for ang in theta_range])
        y_lin_dense = 10**(y_db_dense / 10.0)
        
        y_db_exp = np.array([theoretical.transmission_db_modified(
            ang - offset_val, p_val, d_val, target_freq, ps_val, ls_val) for ang in exp_ang_f])
        y_lin_exp = 10**(y_db_exp / 10.0)
        
        res_lin = (exp_trans_f - y_lin_exp) * 100.0
        res_db = exp_trans_db_f - y_db_exp
        
        line_lin.set_ydata(y_lin_dense)
        line_db.set_ydata(y_db_dense)
        
        for bar, val_lin in zip(bars_lin, res_lin):
            bar.set_height(val_lin)
        for bar, val_db in zip(bars_db, res_db):
            bar.set_height(val_db)
            
        for ax in [ax_res_lin, ax_res_db]:
            for line in list(ax.lines):
                line.remove()
            for collection in list(ax.collections):
                collection.remove()
                
        ax_res_lin.axhline(0, color='red', linestyle='--', linewidth=1.5)
        mean_res_lin = np.mean(res_lin)
        std_res_lin = np.std(res_lin)
        ax_res_lin.axhline(mean_res_lin, color='green', linestyle='--', label=f"Среднее: {mean_res_lin:.2f}%")
        ax_res_lin.fill_between(exp_ang_f, mean_res_lin - std_res_lin, mean_res_lin + std_res_lin,
                                color='green', alpha=0.15, label=f"±1σ: {std_res_lin:.2f}%")
        ax_res_lin.legend(loc='upper right', fontsize=8)
        
        ax_res_db.axhline(0, color='red', linestyle='--', linewidth=1.5)
        mean_res_db = np.mean(res_db)
        std_res_db = np.std(res_db)
        ax_res_db.axhline(mean_res_db, color='green', linestyle='--', label=f"Среднее: {mean_res_db:.2f} дБ")
        ax_res_db.fill_between(exp_ang_f, mean_res_db - std_res_db, mean_res_db + std_res_db,
                                color='green', alpha=0.15, label=f"±1σ: {std_res_db:.2f} дБ")
        ax_res_db.legend(loc='upper right', fontsize=8)
        
        rmse_lin = np.sqrt(np.mean((exp_trans_f - y_lin_exp)**2)) * 100.0
        rmse_db = np.sqrt(np.mean((exp_trans_db_f - y_db_exp)**2))
        
        ax_lin.set_title(f"Линейная шкала (RMSE = {rmse_lin:.2f}%)")
        ax_db.set_title(f"Логарифмическая шкала (RMSE = {rmse_db:.2f} дБ)")
        fig.suptitle(f"Угловая зависимость пропускания и остатки на частоте {target_freq:.2f} ТГц")
        
        fig.canvas.draw_idle()
        
    slider_f.on_changed(update)
    slider_p.on_changed(update)
    slider_d.on_changed(update)
    slider_ps.on_changed(update)
    slider_ls.on_changed(update)
    slider_offset.on_changed(update)
    
    ax_opt = plt.axes([0.72, 0.12, 0.11, 0.08])
    btn_opt = Button(ax_opt, 'Подогнать ν', color='lightgreen', hovercolor='lime')
    
    def optimize_callback(event):
        target_freq = slider_f.val
        p_cur = slider_p.val * 1e-6
        d_cur = slider_d.val * 1e-6
        ps_cur = slider_ps.val
        ls_cur = slider_ls.val
        offset_cur = slider_offset.val
        
        initial_guess = [p_cur, d_cur, ps_cur, ls_cur, offset_cur]
        bounds = [
            (5e-6, 30e-6),
            (1e-6, 15e-6),
            (0.5, 2.0),
            (0.0, 5.0),
            (-15.0, 15.0)
        ]
        
        opt_ang_f, opt_trans_f = get_experimental_transmission_at_freq(spectra, target_freq)
        opt_trans_db_f = 10 * np.log10(np.maximum(opt_trans_f, 1e-12))
        
        def loss_function(params):
            p, d, ps, ls, offset = params
            if d >= p * ps:
                return 1e6
            y_db = np.array([theoretical.transmission_db_modified(
                ang - offset, p, d, target_freq, ps, ls) for ang in opt_ang_f])
            return np.sqrt(np.mean((opt_trans_db_f - y_db)**2))
            
        print(f"Запуск оптимизации Nelder-Mead на частоте {target_freq:.2f} ТГц...")
        res = minimize(loss_function, initial_guess, method='Nelder-Mead', bounds=bounds, tol=1e-2)
        
        if res.success:
            opt_p, opt_d, opt_ps, opt_ls, opt_offset = res.x
            print(f"Успешно! RMSE: {res.fun:.4f} dB")
            slider_p.set_val(opt_p * 1e6)
            slider_d.set_val(opt_d * 1e6)
            slider_ps.set_val(opt_ps)
            slider_ls.set_val(opt_ls)
            slider_offset.set_val(opt_offset)
        else:
            print("Оптимизация не сошлась:", res.message)
            
    btn_opt.on_clicked(optimize_callback)
    
    ax_next = plt.axes([0.85, 0.12, 0.10, 0.08])
    btn_next = Button(ax_next, 'Далее ➔', color='lightblue', hovercolor='skyblue')
    
    def next_callback(event):
        plt.close(fig)
        
    btn_next.on_clicked(next_callback)
    
    update(0)
    plt.show()
    return result

def run_step4_batch_optimization(spectra, init_params):
    print("\n--- Шаг 4: Пакетная оптимизация по всему спектру частот ---")
    freq_start, freq_end = 0.2, 1.8
    
    raw_keys = sorted(list(spectra.keys()))
    angles = np.array([k[0] for k in raw_keys])
    
    freqs = spectra[raw_keys[0]][0]
    target_indices = np.where((freqs >= freq_start) & (freqs <= freq_end))[0]
    
    # Спектр БПФ содержит 1600 точек; пакетная оптимизация по всем точкам слишком медленная.
    # Разрежаем частотный диапазон, выбирая каждую 20-ю точку спектра.
    step = 20
    target_indices = target_indices[::step]
    analysis_freqs = freqs[target_indices]
    
    opt_p_arr = []
    opt_d_arr = []
    opt_scale_arr = []
    opt_loss_arr = []
    opt_offset_arr = []
    rmse_db_arr = []
    
    p_guess = init_params['p']
    d_guess = init_params['d']
    scale_guess = init_params['period_scale']
    loss_guess = init_params['loss_factor']
    offset_guess = init_params['theta_offset']
    
    bounds = [
        (5e-6, 30e-6),
        (1e-6, 15e-6),
        (0.5, 2.0),
        (0.0, 5.0),
        (-15.0, 15.0)
    ]
    
    print(f"Запуск разреженного пакетного фита для {len(analysis_freqs)} частот...")
    
    for f_idx in target_indices:
        f_val = freqs[f_idx]
        exp_trans = []
        for k in raw_keys:
            exp_trans.append(spectra[k][1][f_idx])
        exp_trans = np.array(exp_trans)
        exp_trans_db = 10 * np.log10(np.maximum(exp_trans, 1e-12))
        
        def loss_func(params):
            p, d, ps, ls, offset = params
            if d >= p * ps:
                return 1e6
            y_db = np.array([theoretical.transmission_db_modified(
                ang - offset, p, d, f_val, ps, ls) for ang in angles])
            return np.sqrt(np.mean((exp_trans_db - y_db)**2))
            
        initial_guess = [p_guess, d_guess, scale_guess, loss_guess, offset_guess]
        res = minimize(loss_func, initial_guess, method='Nelder-Mead', bounds=bounds, tol=1e-2)
        
        if res.success:
            opt_p, opt_d, opt_ps, opt_ls, opt_offset = res.x
            p_guess, d_guess, scale_guess, loss_guess, offset_guess = opt_p, opt_d, opt_ps, opt_ls, opt_offset
            
            opt_p_arr.append(opt_p * 1e6)
            opt_d_arr.append(opt_d * 1e6)
            opt_scale_arr.append(opt_ps)
            opt_loss_arr.append(opt_ls)
            opt_offset_arr.append(opt_offset)
            rmse_db_arr.append(res.fun)
        else:
            opt_p_arr.append(np.nan)
            opt_d_arr.append(np.nan)
            opt_scale_arr.append(np.nan)
            opt_loss_arr.append(np.nan)
            opt_offset_arr.append(np.nan)
            rmse_db_arr.append(np.nan)
            
    fig, axs = plt.subplots(3, 2, figsize=(14, 10), sharex=True)
    axs = axs.ravel()
    
    axs[0].plot(analysis_freqs, opt_p_arr, 'b-o', markersize=3, label='Вычисленный шаг P')
    axs[0].axhline(config.P_DEFAULT*1e6, color='red', linestyle='--', label='Паспортный шаг')
    axs[0].set_ylabel('Шаг P (мкм)')
    axs[0].set_title('Шаг решетки P')
    axs[0].grid(True)
    axs[0].legend()
    
    axs[1].plot(analysis_freqs, opt_d_arr, 'g-o', markersize=3, label='Вычисленный диаметр D')
    axs[1].axhline(config.D_DEFAULT*1e6, color='red', linestyle='--', label='Паспортный диаметр')
    axs[1].set_ylabel('Диаметр D (мкм)')
    axs[1].set_title('Диаметр проволоки D')
    axs[1].grid(True)
    axs[1].legend()
    
    axs[2].plot(analysis_freqs, opt_scale_arr, 'm-o', markersize=3)
    axs[2].set_ylabel('Масштаб периода P Scale')
    axs[2].set_title('Масштаб периода Period Scale')
    axs[2].grid(True)
    
    axs[3].plot(analysis_freqs, opt_loss_arr, 'c-o', markersize=3)
    axs[3].set_ylabel('Потери Loss')
    axs[3].set_title('Коэффициент затухания Loss')
    axs[3].grid(True)
    
    axs[4].plot(analysis_freqs, opt_offset_arr, 'y-o', markersize=3)
    axs[4].set_ylabel('Смещение поляризатора (°)')
    axs[4].set_title('Систематическое смещение угла Theta Offset')
    axs[4].grid(True)
    
    axs[5].plot(analysis_freqs, rmse_db_arr, 'r-o', markersize=3, label='RMSE подгонки')
    axs[5].set_ylabel('RMSE (дБ)')
    axs[5].set_xlabel('Частота (ТГц)')
    axs[5].set_title('Качество аппроксимации (RMSE в дБ)')
    axs[5].grid(True)
    axs[5].legend()
    
    mean_p = np.nanmean(opt_p_arr)
    mean_d = np.nanmean(opt_d_arr)
    mean_rmse = np.nanmean(rmse_db_arr)
    mean_offset = np.nanmean(opt_offset_arr)
    
    fig.suptitle(f'Результаты пакетной оптимизации параметров поляризатора\n'
                 f'Средние: P = {mean_p:.2f} мкм, D = {mean_d:.2f} мкм, Offset = {mean_offset:.2f}° (RMSE = {mean_rmse:.2f} дБ)',
                 fontsize=14, fontweight='bold')
                 
    plt.tight_layout()
    plt.show()

def main():
    print("=================================================================")
    print("Запуск интегрированного сквозного приложения обработки ТГц данных")
    print("=================================================================")
    
    signals_raw, backgrounds = load_first_repetition_dataset(config.DATA_DIR)
    signals_avg, backgrounds_avg = load_and_average_dataset(config.DATA_DIR)
    
    if not signals_raw or not backgrounds:
        print("Ошибка: данные для анализа не найдены!")
        return
        
    # Шаг 1: Фильтрация во временной области на первом повторении сигналов
    win_params = run_step1_time_domain(signals_raw, backgrounds)
    
    # Шаг 2: Спектральный анализ на усредненных по всем проходам сигналах
    dsp_params = run_step2_frequency_domain(signals_avg, backgrounds_avg, win_params)
    
    spectra = compute_spectra_with_params(
        signals_avg, backgrounds_avg, 
        pad_factor=dsp_params['pad_factor'], 
        sigma=dsp_params['sigma']
    )
    
    fit_params = run_step3_interactive_fit(spectra, dsp_params['pad_factor'])
    run_step4_batch_optimization(spectra, fit_params)
    
    print("\nИнтегрированная обработка успешно завершена!")

if __name__ == '__main__':
    # Настроим неинтерактивный бэкенд для тестов
    import sys
    if '--test' in sys.argv or 'test' in sys.argv:
        import matplotlib
        matplotlib.use('Agg')
    main()
