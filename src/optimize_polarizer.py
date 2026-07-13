"""
=============================================================================
Двухполяризаторный аттенюатор ТГц: трёхэтапная оптимизация параметров
=============================================================================
Этап 1: Линейная шкала  | 4 параметра: p_eff, d_eff, α, γ
Этап 2: дБ-шкала        | те же 4, жёсткие границы из этапа 1
Этап 3: дБ + аппаратная | 6 параметров: + θ_offset, ε_floor
=============================================================================
"""

import sys, os, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize, approx_fprime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ─── Утилиты логирования ──────────────────────────────────────────────────────
_T0 = time.time()

def log(msg='', **kw):
    """Печатает сообщение с меткой прошедшего времени и сразу сбрасывает буфер."""
    elapsed = time.time() - _T0
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    prefix = f"[{h:02d}:{m:02d}:{s:02d}]"
    print(f"{prefix}  {msg}", flush=True, **kw)

# ─── Настройки отображения ────────────────────────────────────────────────────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

plt.rcParams.update({
    'font.family':       'serif',
    'font.size':         11,
    'axes.linewidth':    1.0,
    'xtick.direction':   'in',
    'ytick.direction':   'in',
    'xtick.top':         True,
    'ytick.right':       True,
    'xtick.major.size':  4,
    'ytick.major.size':  4,
    'figure.dpi':        150,
})

# ─── Пути (автоматически определяются относительно расположения скрипта) ──────
# Скрипт лежит в src/, данные — в src/data/, графики — в src/results/
THIS_DIR = Path(__file__).resolve().parent   # .../src/
DATA_DIR = THIS_DIR / "data"
OUT_DIR  = THIS_DIR / "results"
OUT_DIR.mkdir(exist_ok=True)

# Модуль theoretical.py лежит рядом в той же папке src/
sys.path.insert(0, str(THIS_DIR))
import theoretical

C_LIGHT = 3e8   # м/с

# ─── БЛОК 1: ЗАГРУЗКА ДАННЫХ СЕРИИ 2 ─────────────────────────────────────────

def load_tds(path: Path):
    """Загружает файл ТГц-данных, вычитает постоянную составляющую."""
    raw = np.loadtxt(path)
    t, E = raw[:, 0], raw[:, 1]
    E -= np.mean(E[:50])
    return t, E

def load_series2():
    """
    Находит все файлы серии 2 (0–90°), загружает образец и его
    парный фоновый файл, вычисляет T_Σ = ∫E²_s dt / ∫E²_bg dt.
    Возвращает: angles (array), T_exp (array), bg_files (dict)
    """
    angles, T_list, bg_dict = [], [], {}

    all_files = sorted(f for f in os.listdir(DATA_DIR)
                       if '-0-2-' in f and f.endswith('.txt'))

    for fname in all_files:
        angle_deg = int(fname.split('-')[0])
        if not (0 <= angle_deg <= 90):
            continue

        # Парный фон закодирован в имени: "0-0-2-bg_7.txt" → bg = "bg_7.txt"
        bg_name = fname.split('-', 3)[-1]          # "bg_7.txt"
        bg_path = DATA_DIR / bg_name

        if not bg_path.exists():
            print(f"[WARN] Фон не найден: {bg_path}, пропускаем {fname}")
            continue

        t_s, E_s = load_tds(DATA_DIR / fname)
        t_b, E_b = load_tds(bg_path)

        E_s_int = np.trapezoid(E_s**2, t_s)
        E_b_int = np.trapezoid(E_b**2, t_b)

        angles.append(angle_deg)
        T_list.append(E_s_int / E_b_int)
        bg_dict[angle_deg] = bg_path

    # Сортируем по углу
    order   = np.argsort(angles)
    angles  = np.array(angles)[order]
    T_exp   = np.array(T_list)[order]
    bg_dict = {angles[i]: bg_dict[angles[i]] for i in range(len(angles))}

    return angles, T_exp, bg_dict

# ─── БЛОК 2: СПЕКТРАЛЬНЫЙ БАЗИС И ТЕОРЕТИЧЕСКИЙ T_Σ ─────────────────────────

def build_spectral_basis(bg_path: Path, f_min=0.2, f_max=1.8):
    """
    Строит массив частот и весовой спектр |E_bg(ν)|² из фонового файла.
    Возвращает: freqs_THz, weights (нормированные)
    """
    t, E = load_tds(bg_path)
    dt   = t[1] - t[0]
    N    = len(t)
    fft  = np.fft.rfft(E)
    freq = np.fft.rfftfreq(N, dt)          # в тех же единицах, что и t (пс → ТГц)

    mask    = (freq >= f_min) & (freq <= f_max)
    freqs   = freq[mask]
    weights = np.abs(fft[mask])**2
    return freqs, weights

def theory_T_integral(angle_deg, p_eff_m, d_eff_m, alpha, gamma,
                      freqs_THz, weights,
                      theta_offset_deg=0.0, eps_floor=0.0):
    """
    Интегральное пропускание модели Бланко, взвешенное по спектру фона.

        T_Σ = [∫ T_Blanco(ν,θ+Δθ) · exp(-α·ν^γ) · W(ν) dν] / [∫ W(ν) dν]
              + ε_floor

    Параметры
    ----------
    p_eff_m  : шаг решётки [м]
    d_eff_m  : диаметр проволоки [м]
    alpha    : коэффициент потерь [ТГц^{-γ}]
    gamma    : показатель степени частотной зависимости потерь
    freqs_THz: массив частот [ТГц]
    weights  : |E_bg(ν)|² (не нормированные)
    theta_offset_deg: угловое смещение лимба [°]
    eps_floor: шумовой предел детектора (аддитивный, безразмерный)
    """
    theta_rad = np.deg2rad(angle_deg + theta_offset_deg)
    T_blanco  = np.empty(len(freqs_THz))

    for i, nu in enumerate(freqs_THz):
        lam          = C_LIGHT / (nu * 1e12)      # длина волны [м]
        p_over_lam   = p_eff_m / lam
        d_over_p     = d_eff_m / p_eff_m
        T_blanco[i]  = theoretical.transmission_two_polarizers(
                           theta_rad, p_over_lam, d_over_p, N=10)

    loss         = np.exp(-alpha * freqs_THz**gamma)
    T_model      = T_blanco * loss               # T(ν,θ)
    numerator    = np.trapezoid(T_model * weights, freqs_THz)
    denominator  = np.trapezoid(weights,           freqs_THz)

    return float(numerator / denominator) + eps_floor

# ─── БЛОК 3: ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ─────────────────────────────────────────

def build_theory_curve(angles, p_eff_m, d_eff_m, alpha, gamma,
                       freqs_THz, weights,
                       theta_offset_deg=0.0, eps_floor=0.0):
    return np.array([
        theory_T_integral(a, p_eff_m, d_eff_m, alpha, gamma,
                          freqs_THz, weights, theta_offset_deg, eps_floor)
        for a in angles])

def param_uncertainties(loss_fn, x_opt, param_names, eps=1e-5):
    """
    Оценка стандартных отклонений параметров через диагональ обратного
    гессиана (метод конечных разностей).
    """
    n   = len(x_opt)
    H   = np.zeros((n, n))
    f0  = loss_fn(x_opt)
    dx  = np.abs(x_opt) * eps + 1e-10
    total_calls = n * n
    call_idx    = 0

    log(f"  Гессиан: {n}×{n} = {total_calls} пар вычислений...")
    for i in range(n):
        for j in range(n):
            x1, x2, x3, x4 = x_opt.copy(), x_opt.copy(), x_opt.copy(), x_opt.copy()
            x1[i] += dx[i]; x1[j] += dx[j]
            x2[i] += dx[i]; x2[j] -= dx[j]
            x3[i] -= dx[i]; x3[j] += dx[j]
            x4[i] -= dx[i]; x4[j] -= dx[j]
            H[i, j] = (loss_fn(x1) - loss_fn(x2) - loss_fn(x3) + loss_fn(x4)) \
                      / (4 * dx[i] * dx[j])
            call_idx += 1
            if call_idx % max(1, total_calls // 5) == 0:
                pct = 100 * call_idx / total_calls
                log(f"    {pct:.0f}%  [{call_idx}/{total_calls}]  "
                    f"({param_names[i]} x {param_names[j]})")

    try:
        H_inv = np.linalg.inv(H)
        sigmas = np.sqrt(np.maximum(np.diag(H_inv) * f0 / max(len(x_opt) - n, 1), 0))
    except np.linalg.LinAlgError:
        sigmas = np.full(n, np.nan)
    return sigmas

# ─── БЛОК 4: ФУНКЦИИ ОТРИСОВКИ ───────────────────────────────────────────────

def plot_fit(angles_exp, T_exp, T_theory, residuals, title, ylabel_top,
             ylabel_bot, filename, db_scale=False):
    fig = plt.figure(figsize=(7, 5.5))
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    ang_dense = np.linspace(angles_exp.min(), angles_exp.max(), 200)

    ax1.plot(angles_exp, T_exp,    'ko',  ms=6, mfc='white', label='Эксперимент', zorder=5)
    ax1.plot(angles_exp, T_theory, 'k--', lw=1.5, label='Модель Бланко')
    ax1.set_ylabel(ylabel_top)
    ax1.legend(frameon=True, edgecolor='black', fontsize=10)
    ax1.grid(True, ls=':', lw=0.6, color='gray')
    ax1.set_title(title, fontsize=11)
    plt.setp(ax1.get_xticklabels(), visible=False)

    ax2.axhline(0, color='gray', ls=':', lw=0.8)
    ax2.bar(angles_exp, residuals, width=5, color='black', alpha=0.55)
    ax2.set_ylabel(ylabel_bot)
    ax2.set_xlabel('Угол поворота $\\theta$ (°)')
    ax2.grid(True, ls=':', lw=0.6, color='gray')

    plt.savefig(OUT_DIR / filename, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Сохранено: {filename}")

# ─── БЛОК 5: ГЛАВНЫЙ АЛГОРИТМ ────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("  Трёхэтапная оптимизация поляризационного аттенюатора")
    log("=" * 60)

    # ── Загрузка экспериментальных данных ─────────────────────────────────
    log("")
    log("[1] Загрузка данных серии 2...")
    angles_exp, T_exp, bg_dict = load_series2()
    T_exp_dB = 10 * np.log10(np.maximum(T_exp, 1e-12))

    log(f"    Загружено точек: {len(angles_exp)}")
    log(f"    Углы: {angles_exp} °")
    for i, a in enumerate(angles_exp):
        log(f"    θ={a:3d}°  T={T_exp[i]:.5f}  ({T_exp_dB[i]:.2f} дБ)")

    # ── Спектральный базис — берём один фоновый файл (первый в списке) ────
    sample_bg = list(bg_dict.values())[0]
    freqs_THz, weights = build_spectral_basis(sample_bg)
    log(f"    Спектральный диапазон: {freqs_THz[0]:.2f}–{freqs_THz[-1]:.2f} ТГц"
        f"  ({len(freqs_THz)} точек)")

    # ═══════════════════════════════════════════════════════════════════════
    # ЭТАП 1: Оптимизация в линейном масштабе
    # ═══════════════════════════════════════════════════════════════════════
    log("")
    log("─" * 60)
    log("  ЭТАП 1: Линейная шкала (4 параметра)")
    log("─" * 60)

    # Начальные значения и границы
    # p_eff = 16 ± 2 мкм, d_eff = 5.5 ± 0.5 мкм
    P0_M   = 16e-6;  P_LO_M  = 14e-6;  P_HI_M  = 18e-6
    D0_M   = 5.5e-6; D_LO_M  = 5.0e-6; D_HI_M  = 6.0e-6
    A0     = 0.05;   A_LO    = 0.0;    A_HI    = 5.0
    G0     = 1.5;    G_LO    = 1.0;    G_HI    = 2.0

    x0_s1  = [P0_M, D0_M, A0, G0]
    bnd_s1 = [(P_LO_M, P_HI_M), (D_LO_M, D_HI_M), (A_LO, A_HI), (G_LO, G_HI)]

    iter_count = [0]
    t_stage_start = [time.time()]

    def cb1(xk):
        iter_count[0] += 1
        if iter_count[0] % 10 == 0:
            elapsed = time.time() - t_stage_start[0]
            log(f"    iter {iter_count[0]:4d}  |  "
                f"p={xk[0]*1e6:.2f} мкм  d={xk[1]*1e6:.2f} мкм  "
                f"α={xk[2]:.4f}  γ={xk[3]:.4f}  "
                f"({elapsed:.0f}с)")

    def objective_linear(x):
        p, d, a, g = x
        err = 0.0
        for i, ang in enumerate(angles_exp):
            T_th = theory_T_integral(ang, p, d, a, g, freqs_THz, weights)
            err += (T_th - T_exp[i])**2
        return err

    log("  Оптимизация (печатает каждые 10 итераций)...")
    iter_count[0] = 0; t_stage_start[0] = time.time()
    res1 = minimize(objective_linear, x0_s1, bounds=bnd_s1, method='L-BFGS-B',
                    callback=cb1,
                    options={'maxiter': 2000, 'ftol': 1e-14, 'gtol': 1e-10})
    p1, d1, a1, g1 = res1.x
    log(f"  Оптимизация завершена за {iter_count[0]} итераций.")

    log("  Вычисление погрешностей (гессиан)...")
    names1 = ['p','d','α','γ']
    sigma1 = param_uncertainties(objective_linear, res1.x, names1)
    sp1, sd1, sa1, sg1 = sigma1

    T_th_s1   = build_theory_curve(angles_exp, p1, d1, a1, g1, freqs_THz, weights)
    resid_s1  = T_th_s1 - T_exp

    log(f"")
    log(f"  Результаты этапа 1:")
    log(f"    p_eff = ({p1*1e6:.3f} ± {sp1*1e6:.4f}) мкм")
    log(f"    d_eff = ({d1*1e6:.3f} ± {sd1*1e6:.4f}) мкм")
    log(f"    α     = ({a1:.4f} ± {sa1:.4f}) ТГц⁻ᵞ")
    log(f"    γ     = ({g1:.4f} ± {sg1:.4f})")
    log(f"    RMSE  = {np.sqrt(np.mean(resid_s1**2)):.5f}")

    plot_fit(
        angles_exp, T_exp, T_th_s1, resid_s1,
        title='Этап 1: Линейная оптимизация',
        ylabel_top='$T_\\Sigma(\\theta)$',
        ylabel_bot='Невязка $\\Delta T$',
        filename='optim_stage1_linear.png',
        db_scale=False
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ЭТАП 2: Оптимизация в дБ-масштабе
    # Те же 4 параметра, но границы = результат ± 3σ этапа 1
    # ═══════════════════════════════════════════════════════════════════════
    log("")
    log("─" * 60)
    log("  ЭТАП 2: Логарифмический масштаб (4 параметра, жёсткие границы)")
    log("─" * 60)

    k_sigma = 3.0   # доверительный множитель

    def tight_bounds(val, sig, lo_abs, hi_abs):
        lo = max(val - k_sigma * abs(sig), lo_abs)
        hi = min(val + k_sigma * abs(sig), hi_abs)
        if lo >= hi:
            lo, hi = val * 0.98, val * 1.02
        return (lo, hi)

    bnd_s2 = [
        tight_bounds(p1, sp1, 1e-6,  50e-6),
        tight_bounds(d1, sd1, 0.1e-6, 20e-6),
        tight_bounds(a1, sa1, 0.0,    10.0),
        tight_bounds(g1, sg1, 0.5,     3.0),
    ]
    x0_s2 = [p1, d1, a1, g1]

    def cb2(xk):
        iter_count[0] += 1
        if iter_count[0] % 10 == 0:
            elapsed = time.time() - t_stage_start[0]
            log(f"    iter {iter_count[0]:4d}  |  "
                f"p={xk[0]*1e6:.2f} мкм  d={xk[1]*1e6:.2f} мкм  "
                f"α={xk[2]:.4f}  γ={xk[3]:.4f}  "
                f"({elapsed:.0f}с)")

    def objective_db(x):
        p, d, a, g = x
        err = 0.0
        for i, ang in enumerate(angles_exp):
            T_th  = theory_T_integral(ang, p, d, a, g, freqs_THz, weights)
            db_th = 10 * np.log10(max(T_th, 1e-12))
            err  += (db_th - T_exp_dB[i])**2
        return err

    log("  Оптимизация (печатает каждые 10 итераций)...")
    iter_count[0] = 0; t_stage_start[0] = time.time()
    res2 = minimize(objective_db, x0_s2, bounds=bnd_s2, method='L-BFGS-B',
                    callback=cb2,
                    options={'maxiter': 2000, 'ftol': 1e-14, 'gtol': 1e-10})
    p2, d2, a2, g2 = res2.x
    log(f"  Оптимизация завершена за {iter_count[0]} итераций.")

    log("  Вычисление погрешностей (гессиан)...")
    names2 = ['p','d','α','γ']
    sigma2 = param_uncertainties(objective_db, res2.x, names2)
    sp2, sd2, sa2, sg2 = sigma2

    T_th_s2    = build_theory_curve(angles_exp, p2, d2, a2, g2, freqs_THz, weights)
    T_th_s2_dB = 10 * np.log10(np.maximum(T_th_s2, 1e-12))
    resid_s2   = T_th_s2_dB - T_exp_dB

    log(f"")
    log(f"  Результаты этапа 2:")
    log(f"    p_eff = ({p2*1e6:.3f} ± {sp2*1e6:.4f}) мкм")
    log(f"    d_eff = ({d2*1e6:.3f} ± {sd2*1e6:.4f}) мкм")
    log(f"    α     = ({a2:.4f} ± {sa2:.4f}) ТГц⁻ᵞ")
    log(f"    γ     = ({g2:.4f} ± {sg2:.4f})")
    log(f"    RMSE  = {np.sqrt(np.mean(resid_s2**2)):.4f} дБ")

    plot_fit(
        angles_exp, T_exp_dB, T_th_s2_dB, resid_s2,
        title='Этап 2: Логарифмическая оптимизация',
        ylabel_top='Затухание (дБ)',
        ylabel_bot='Невязка (дБ)',
        filename='optim_stage2_db.png',
        db_scale=True
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ЭТАП 3: дБ + аппаратная функция (6 параметров)
    # Добавляем θ_offset [°] и ε_floor [б/р]
    # ═══════════════════════════════════════════════════════════════════════
    log("")
    log("─" * 60)
    log("  ЭТАП 3: Аппаратная функция (6 параметров)")
    log("─" * 60)

    bnd_s3 = [
        tight_bounds(p2, sp2, 1e-6,  50e-6),
        tight_bounds(d2, sd2, 0.1e-6, 20e-6),
        tight_bounds(a2, sa2, 0.0,    10.0),
        tight_bounds(g2, sg2, 0.5,     3.0),
        (-5.0, 5.0),          # θ_offset [°] — свободно в разумных пределах
        (0.0,  1e-2),         # ε_floor — от 0 до 1% от мощности фона
    ]
    x0_s3 = [p2, d2, a2, g2, 0.0, 1e-5]

    def cb3(xk):
        iter_count[0] += 1
        if iter_count[0] % 10 == 0:
            elapsed = time.time() - t_stage_start[0]
            log(f"    iter {iter_count[0]:4d}  |  "
                f"p={xk[0]*1e6:.2f}мкм  d={xk[1]*1e6:.2f}мкм  "
                f"α={xk[2]:.4f}  γ={xk[3]:.4f}  "
                f"Δθ={xk[4]:.3f}°  ε={xk[5]:.2e}  "
                f"({elapsed:.0f}с)")

    def objective_db_hw(x):
        p, d, a, g, th_off, eps_fl = x
        err = 0.0
        for i, ang in enumerate(angles_exp):
            T_th  = theory_T_integral(ang, p, d, a, g, freqs_THz, weights,
                                      theta_offset_deg=th_off, eps_floor=eps_fl)
            db_th = 10 * np.log10(max(T_th, 1e-12))
            err  += (db_th - T_exp_dB[i])**2
        return err

    log("  Оптимизация (печатает каждые 10 итераций)...")
    iter_count[0] = 0; t_stage_start[0] = time.time()
    res3 = minimize(objective_db_hw, x0_s3, bounds=bnd_s3, method='L-BFGS-B',
                    callback=cb3,
                    options={'maxiter': 3000, 'ftol': 1e-15, 'gtol': 1e-11})
    p3, d3, a3, g3, th3, eps3 = res3.x
    log(f"  Оптимизация завершена за {iter_count[0]} итераций.")

    log("  Вычисление погрешностей (гессиан)...")
    names3 = ['p','d','α','γ','Δθ','ε']
    sigma3 = param_uncertainties(objective_db_hw, res3.x, names3)
    sp3, sd3, sa3, sg3, sth3, seps3 = sigma3

    T_th_s3    = build_theory_curve(angles_exp, p3, d3, a3, g3,
                                    freqs_THz, weights, th3, eps3)
    T_th_s3_dB = 10 * np.log10(np.maximum(T_th_s3, 1e-12))
    resid_s3   = T_th_s3_dB - T_exp_dB

    log(f"")
    log(f"  Результаты этапа 3 (итог):")
    log(f"    p_eff     = ({p3*1e6:.3f} ± {sp3*1e6:.4f}) мкм")
    log(f"    d_eff     = ({d3*1e6:.3f} ± {sd3*1e6:.4f}) мкм")
    log(f"    α         = ({a3:.4f} ± {sa3:.4f}) ТГц⁻ᵞ")
    log(f"    γ         = ({g3:.4f} ± {sg3:.4f})")
    log(f"    θ_offset  = ({th3:.3f} ± {sth3:.4f}) °")
    log(f"    ε_floor   = ({eps3:.3e} ± {seps3:.2e})")
    log(f"    RMSE      = {np.sqrt(np.mean(resid_s3**2)):.4f} дБ")

    plot_fit(
        angles_exp, T_exp_dB, T_th_s3_dB, resid_s3,
        title='Этап 3: Аппаратная функция (полная модель)',
        ylabel_top='Затухание (дБ)',
        ylabel_bot='Невязка (дБ)',
        filename='optim_stage3_hw.png',
        db_scale=True
    )

    # ─── Итоговая таблица ─────────────────────────────────────────────────
    total_time = time.time() - _T0
    log("")
    log("=" * 60)
    log("  ИТОГОВЫЕ ПАРАМЕТРЫ МОДЕЛИ")
    log("=" * 60)
    log(f"  {'Параметр':<16} {'Этап 1':>13} {'Этап 2':>13} {'Этап 3':>13}")
    log("  " + "-" * 57)
    log(f"  {'p_eff (мкм)':<16} {p1*1e6:>10.3f}   {p2*1e6:>10.3f}   {p3*1e6:>10.3f}")
    log(f"  {'d_eff (мкм)':<16} {d1*1e6:>10.3f}   {d2*1e6:>10.3f}   {d3*1e6:>10.3f}")
    log(f"  {'α':<16} {a1:>10.4f}   {a2:>10.4f}   {a3:>10.4f}")
    log(f"  {'γ':<16} {g1:>10.4f}   {g2:>10.4f}   {g3:>10.4f}")
    log(f"  {'θ_offset (°)':<16} {'—':>10}   {'—':>10}   {th3:>10.3f}")
    log(f"  {'ε_floor':<16} {'—':>10}   {'—':>10}   {eps3:>10.2e}")
    log("=" * 60)
    log(f"  Общее время выполнения: {total_time/60:.1f} мин ({total_time:.0f} с)")

if __name__ == "__main__":
    main()
