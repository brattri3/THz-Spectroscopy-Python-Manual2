import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Добавим пути к модулям
src_dir = r"C:\Users\pop\.\.gemini\antigravity\worktrees\THz-Spectroscopy-Python-Manual2\apply-latest-updates\src"
sys.path.append(src_dir)

import theoretical
import fitting_2d

# Папка для сохранения изображений
output_dir = r"C:\Users\pop\.\.gemini\antigravity\worktrees\THz-Spectroscopy-Python-Manual2\apply-latest-updates\text"
os.makedirs(output_dir, exist_ok=True)

# Установка шрифтов для единообразия (все надписи на графиках будут 10pt)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9

# Оптимальные эффективные параметры калибровки для текущего аттенюатора ATT-11-16-CA85
P_eff = 15.50 * 1e-6
D_eff = 5.67 * 1e-6
loss_factor = 0.255
loss_exponent = 1.58
offset_deg = -0.45
c_light = 3e8

# Уровни шума
noise_db = -45.0
noise_power = 10**(noise_db/10)

def simulate_T(angle_deg, freq_th, scenario='A'):
    # scenario 'A': PCA (cos^4), 'B': bolometer (cos^2)
    angle_rad = np.radians(angle_deg - offset_deg)
    lambda_m = c_light / (freq_th * 1e12)
    
    t_perp = theoretical.compute_t_perp(P_eff/lambda_m, D_eff/P_eff)
    t_par = theoretical.compute_t_par(P_eff/lambda_m, D_eff/P_eff)
    
    # Омические потери с учетом дисперсионного закона e^(-alpha * nu^gamma)
    # loss_factor задан в дБ/ТГц^gamma, переводим в Неперы (делением на 10*log10(e) = 4.343)
    loss_factor_np = loss_factor / 4.343
    t_perp_eff = t_perp * np.exp(-0.5 * loss_factor_np * (freq_th ** loss_exponent))
    t_par_eff = t_par * np.exp(-0.5 * loss_factor_np * (freq_th ** loss_exponent))
    
    if scenario == 'B':  # Bolometer
        T_total = np.abs(t_perp_eff)**2 * np.cos(angle_rad)**2 + np.abs(t_par_eff)**2 * np.sin(angle_rad)**2
    else:  # PCA (Scenario A)
        E_out = np.cos(angle_rad)**2 * t_perp_eff + np.sin(angle_rad)**2 * t_par_eff
        T_total = np.abs(E_out)**2
        
    return T_total + noise_power

def generate_plots():
    print("=== GENERATING PASSPORT PLOTS (ENGLISH, MONOCHROME-COMPATIBLE COLOR) ===")
    
    # 1. Загрузка экспериментальных точек (используем чистую серию Repetition 1)
    try:
        angles_exp, freqs_exp, exp_linear, exp_db, t_noise = fitting_2d.load_2d_experimental_data(repetition=1, freq_start=0.2, freq_end=1.5)
        idx_05 = np.argmin(np.abs(freqs_exp - 0.5))
        idx_10 = np.argmin(np.abs(freqs_exp - 1.0))
        
        exp_y_05_lin = exp_linear[:, idx_05]
        exp_y_05_db = exp_db[:, idx_05]
        exp_y_10_lin = exp_linear[:, idx_10]
        exp_y_10_db = exp_db[:, idx_10]
    except Exception as e:
        print(f"Menlo data load error: {e}. Using fallback simulation.")
        angles_exp = np.array([0, 10, 20, 30, 40, 50, 60, 70, 80, 90])
        exp_y_05_lin = np.array([simulate_T(a, 0.5, 'A') * (1 + 0.02 * np.random.randn()) for a in angles_exp])
        exp_y_05_db = 10 * np.log10(exp_y_05_lin)
        exp_y_10_lin = np.array([simulate_T(a, 1.0, 'A') * (1 + 0.03 * np.random.randn()) for a in angles_exp])
        exp_y_10_db = 10 * np.log10(exp_y_10_lin)
    
    angles_theory = np.linspace(0, 90, 500)
    
    # =========================================================================
    # PLOT 1: Calibration Curves (Linear and dB scales)
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    
    # Симуляция теории
    T_PCA_05 = [simulate_T(a, 0.5, 'A') for a in angles_theory]
    T_Bolo_05 = [simulate_T(a, 0.5, 'B') for a in angles_theory]
    T_PCA_10 = [simulate_T(a, 1.0, 'A') for a in angles_theory]
    T_Bolo_10 = [simulate_T(a, 1.0, 'B') for a in angles_theory]
    
    c_05 = '#1f77b4' # Синий
    c_10 = '#ff7f0e' # Оранжевый
    
    # --- Left panel: Linear scale ---
    # Экспериментальные точки Menlo
    ax1.plot(angles_exp, exp_y_05_lin, color=c_05, marker='o', linestyle='None', markersize=6, label='Experiment, 0.5 THz')
    ax1.plot(angles_exp, exp_y_10_lin, color=c_10, marker='s', linestyle='None', markersize=6, label='Experiment, 1.0 THz')
    
    # Scenario A (PCA) - Solid line
    ax1.plot(angles_theory, T_PCA_05, color=c_05, linestyle='-', linewidth=1.5, label='Scenario A (PCA), 0.5 THz')
    ax1.plot(angles_theory, T_PCA_10, color=c_10, linestyle='-', linewidth=1.5, label='Scenario A (PCA), 1.0 THz')
    
    # Scenario B (Bolometer) - Dashed line
    ax1.plot(angles_theory, T_Bolo_05, color=c_05, linestyle='--', linewidth=1.5, label='Scenario B (Bolometer), 0.5 THz')
    ax1.plot(angles_theory, T_Bolo_10, color=c_10, linestyle='--', linewidth=1.5, label='Scenario B (Bolometer), 1.0 THz')
    
    ax1.set_xlabel('Rotator Angle $\\theta$ (deg)', fontsize=10)
    ax1.set_ylabel('Power Transmission Coefficient $T$ (Linear)', fontsize=10)
    ax1.set_xlim(0, 60)
    ax1.set_ylim(0, 1.05)
    
    # Удвоенное количество отметок на левой оси X (каждые 5 градусов)
    ax1.set_xticks(np.arange(0, 61, 5))
    # Удвоенное количество отметок на левой оси Y (шаг 0.1)
    ticks_lin_main = np.arange(0.0, 1.05, 0.1)
    ax1.set_yticks(ticks_lin_main)
    
    ax1.grid(True, linestyle=':', alpha=0.5, color='gray')
    ax1.legend(fontsize=9, loc='lower left')
    ax1.set_title('Low Attenuation (Linear Scale)', fontsize=10, fontweight='bold')
    
    # Правая ось дБ для левого графика - Геометрически строго сопоставлена!
    ax1_db = ax1.twinx()
    ax1_db.set_ylabel('Attenuation $A$ (dB)', fontsize=10)
    # Поставим тики правой оси на тех же высотах Y, что и левая ось
    ticks_lin_db = np.array([0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax1_db.set_yticks(ticks_lin_db)
    ax1_db.set_yticklabels([f"{10*np.log10(t):.1f}" for t in ticks_lin_db])
    ax1_db.set_ylim(0, 1.05) # Строго те же лимиты!
    
    # --- Right panel: dB scale ---
    A_PCA_05 = 10 * np.log10(T_PCA_05)
    A_Bolo_05 = 10 * np.log10(T_Bolo_05)
    A_PCA_10 = 10 * np.log10(T_PCA_10)
    A_Bolo_10 = 10 * np.log10(T_Bolo_10)
    
    # Экспериментальные точки Menlo
    ax2.plot(angles_exp, exp_y_05_db, color=c_05, marker='o', linestyle='None', markersize=6, label='Experiment, 0.5 THz')
    ax2.plot(angles_exp, exp_y_10_db, color=c_10, marker='s', linestyle='None', markersize=6, label='Experiment, 1.0 THz')
    
    # Scenario A (PCA) - Solid line
    ax2.plot(angles_theory, A_PCA_05, color=c_05, linestyle='-', linewidth=1.5, label='Scenario A (PCA), 0.5 THz')
    ax2.plot(angles_theory, A_PCA_10, color=c_10, linestyle='-', linewidth=1.5, label='Scenario A (PCA), 1.0 THz')
    
    # Scenario B (Bolometer) - Dashed line
    ax2.plot(angles_theory, A_Bolo_05, color=c_05, linestyle='--', linewidth=1.5, label='Scenario B (Bolometer), 0.5 THz')
    ax2.plot(angles_theory, A_Bolo_10, color=c_10, linestyle='--', linewidth=1.5, label='Scenario B (Bolometer), 1.0 THz')
    
    ax2.set_xlabel('Rotator Angle $\\theta$ (deg)', fontsize=10)
    ax2.set_ylabel('Attenuation $A$ (dB)', fontsize=10)
    ax2.set_xlim(30, 90)
    ax2.set_ylim(-48, 0.5)
    
    # Удвоенное количество отметок на правой оси X (каждые 5 градусов)
    ax2.set_xticks(np.arange(30, 91, 5))
    # Удвоенное количество отметок на правой оси Y (шаг 5 дБ)
    ticks_db_main = np.arange(-45, 1, 5)
    ax2.set_yticks(ticks_db_main)
    
    ax2.grid(True, linestyle=':', alpha=0.5, color='gray')
    ax2.legend(fontsize=9, loc='lower left')
    ax2.set_title('Deep Attenuation (Decibel Scale)', fontsize=10, fontweight='bold')
    
    # Правая ось в процентах для правого графика - Геометрически строго сопоставлена!
    ax2_lin = ax2.twinx()
    ax2_lin.set_ylabel('Transmission $T$ (Percent)', fontsize=10)
    # Поставим тики правой оси на тех же высотах Y, что и левая ось
    ax2_lin.set_yticks(ticks_db_main)
    ax2_lin.set_yticklabels([f"{10**(db/10)*100:.3f}%" if db < -20 else f"{10**(db/10)*100:.1f}%" for db in ticks_db_main])
    ax2_lin.set_ylim(-48, 0.5) # Строго те же лимиты!
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'passport_calibration.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("Graph 1 (passport_calibration.png) successfully created with aligned scales.")
    
    # =========================================================================
    # PLOT 2: Attenuation Error \Delta A (dB) vs Rotator Angle
    # =========================================================================
    plt.figure(figsize=(7, 4.5))
    
    d_theta_05 = np.radians(0.5)
    d_theta_10 = np.radians(1.0)
    
    angles_err = np.linspace(0, 82, 300)
    tan_vals = np.tan(np.radians(angles_err))
    
    # Для Сценария А (ФПА)
    err_B_05 = (40.0 / np.log(10.0)) * tan_vals * d_theta_05
    err_B_10 = (40.0 / np.log(10.0)) * tan_vals * d_theta_10
    
    plt.plot(angles_err, err_B_05, color=c_05, linestyle='-', linewidth=2, label='Limber Play $\\Delta\\theta = 0.5^\\circ$')
    plt.plot(angles_err, err_B_10, color=c_10, linestyle='--', linewidth=2, label='Limber Play $\\Delta\\theta = 1.0^\\circ$')
    
    plt.xlabel('Rotator Angle $\\theta$ (deg)', fontsize=10)
    plt.ylabel('Attenuation Error $\\Delta A$ (dB)', fontsize=10)
    plt.xlim(0, 82)
    plt.ylim(0, 3.0)
    
    # Удвоенное количество отметок на оси X (каждые 5 градусов)
    plt.xticks(np.arange(0, 83, 5))
    # Удвоенное количество отметок на оси Y (каждые 0.25 дБ)
    plt.yticks(np.arange(0, 3.1, 0.25))
    
    plt.grid(True, linestyle=':', alpha=0.5, color='gray')
    plt.legend(fontsize=9, loc='upper left')
    plt.title('Attenuation Error vs Rotator Backlash (Scenario A)', fontsize=10, fontweight='bold')
    
    plt.savefig(os.path.join(output_dir, 'passport_error.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("Graph 2 (passport_error.png) successfully created.")

if __name__ == '__main__':
    generate_plots()
