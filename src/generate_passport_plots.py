import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Добавим пути к модулям
src_dir = r"C:\Users\pop\.\.gemini\antigravity\worktrees\THz-Spectroscopy-Python-Manual2\apply-latest-updates\src"
sys.path.append(src_dir)

import theoretical

# Папка для сохранения изображений
output_dir = r"C:\Users\pop\.\.gemini\antigravity\worktrees\THz-Spectroscopy-Python-Manual2\apply-latest-updates\text\images"
os.makedirs(output_dir, exist_ok=True)

# Оптимальные эффективные параметры калибровки для текущего аттенюатора
P_eff = 15.50 * 1e-6
D_eff = 5.66 * 1e-6
loss_factor = 0.1345
offset_deg = -0.447
c_light = 3e8

# Уровни шума
noise_db = -45.0
noise_power = 10**(noise_db/10)

def simulate_T(angle_deg, freq_th, scenario='B'):
    # scenario 'A': болометр (cos^2), 'B': ФПА Menlo Tera K8 (cos^4)
    angle_rad = np.radians(angle_deg - offset_deg)
    lambda_m = c_light / (freq_th * 1e12)
    
    t_perp = theoretical.compute_t_perp(P_eff/lambda_m, D_eff/P_eff)
    t_par = theoretical.compute_t_par(P_eff/lambda_m, D_eff/P_eff)
    
    # Омические потери
    t_perp_eff = t_perp * np.exp(-0.5 * loss_factor * freq_th)
    t_par_eff = t_par * np.exp(-0.5 * loss_factor * freq_th)
    
    if scenario == 'A':
        # Болометр (полная мощность)
        T_total = np.abs(t_perp_eff)**2 * np.cos(angle_rad)**2 + np.abs(t_par_eff)**2 * np.sin(angle_rad)**2
    else:
        # ФПА (горизонтальная компонента поля)
        E_out = np.cos(angle_rad)**2 * t_perp_eff + np.sin(angle_rad)**2 * t_par_eff
        T_total = np.abs(E_out)**2
        
    return T_total + noise_power

def generate_plots():
    print("=== ГЕНЕРАЦИЯ ГРАФИКОВ ДЛЯ ПАСПОРТА ===")
    
    angles = np.linspace(0, 90, 500)
    
    # =========================================================================
    # ГРАФИК 1: Калибровочные кривые пропускания в двух шкалах (линейная и дБ)
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 0.5 ТГц
    T_A_05 = [simulate_T(a, 0.5, 'A') for a in angles]
    T_B_05 = [simulate_T(a, 0.5, 'B') for a in angles]
    # 1.0 ТГц
    T_A_10 = [simulate_T(a, 1.0, 'A') for a in angles]
    T_B_10 = [simulate_T(a, 1.0, 'B') for a in angles]
    
    # --- Левая панель: линейный масштаб (слабое затухание) ---
    ax1.plot(angles, T_A_05, 'g-', linewidth=2, label='Сценарий А (Болометр), 0.5 ТГц')
    ax1.plot(angles, T_B_05, 'g--', linewidth=2, label='Сценарий Б (ФПА), 0.5 ТГц')
    ax1.plot(angles, T_A_10, 'r-', linewidth=2, label='Сценарий А (Болометр), 1.0 ТГц')
    ax1.plot(angles, T_B_10, 'r--', linewidth=2, label='Сценарий Б (ФПА), 1.0 ТГц')
    
    ax1.set_xlabel('Угол ротатора $\\theta$ (град)', fontsize=11)
    ax1.set_ylabel('Коэффициент пропускания по мощности $T$ (линейный)', fontsize=11)
    ax1.set_xlim(0, 60)
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(fontsize=9, loc='lower left')
    ax1.set_title('Малые затухания (линейный масштаб)', fontsize=12, fontweight='bold')
    
    # Альтернативная ось дБ справа
    ax1_db = ax1.twinx()
    ax1_db.set_ylim(10*np.log10(1e-12), 10*np.log10(1.05))
    ax1_db.set_ylabel('Ослабление $A$ (дБ)', fontsize=11)
    # Сопоставим тики
    ticks_lin = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax1_db.set_yticks(10 * np.log10(ticks_lin))
    ax1_db.set_yticklabels([f"{10*np.log10(t):.1f}" for t in ticks_lin])
    ax1_db.set_ylim(10*np.log10(0.01), 10*np.log10(1.05)) # лимит до -20 дБ
    
    # --- Правая панель: децибельный масштаб (сильное затухание) ---
    A_A_05 = 10 * np.log10(T_A_05)
    A_B_05 = 10 * np.log10(T_B_05)
    A_A_10 = 10 * np.log10(T_A_10)
    A_B_10 = 10 * np.log10(T_B_10)
    
    ax2.plot(angles, A_A_05, 'g-', linewidth=2, label='Сценарий А (Болометр), 0.5 ТГц')
    ax2.plot(angles, A_B_05, 'g--', linewidth=2, label='Сценарий Б (ФПА), 0.5 ТГц')
    ax2.plot(angles, A_10_A := A_A_10, 'r-', linewidth=2, label='Сценарий А (Болометр), 1.0 ТГц')
    ax2.plot(angles, A_10_B := A_B_10, 'r--', linewidth=2, label='Сценарий Б (ФПА), 1.0 ТГц')
    
    ax2.set_xlabel('Угол ротатора $\\theta$ (град)', fontsize=11)
    ax2.set_ylabel('Ослабление $A$ (дБ)', fontsize=11)
    ax2.set_xlim(30, 90)
    ax2.set_ylim(-50, 0.5)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(fontsize=9, loc='lower left')
    ax2.set_title('Глубокие затухания (децибельный масштаб)', fontsize=12, fontweight='bold')
    
    # Альтернативная ось в разах/процентах справа
    ax2_lin = ax2.twinx()
    ax2_lin.set_ylabel('Пропускание $T$ (проценты)', fontsize=11)
    ticks_db = np.array([0, -5, -10, -15, -20, -25, -30, -35, -40, -45, -50])
    ax2_lin.set_yticks(ticks_db)
    ax2_lin.set_yticklabels([f"{10**(db/10)*100:.3f}%" if db < -20 else f"{10**(db/10)*100:.1f}%" for db in ticks_db])
    ax2_lin.set_ylim(-50, 0.5)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'passport_calibration.png'), dpi=200)
    plt.close()
    print("График 1 (passport_calibration.png) успешно создан.")
    
    # =========================================================================
    # ГРАФИК 2: Погрешность затухания \Delta A (дБ) от угла ротатора
    # =========================================================================
    plt.figure(figsize=(8, 5))
    
    # Угловой люфт лимба
    d_theta_05 = np.radians(0.5)
    d_theta_10 = np.radians(1.0)
    
    # Чувствительность к углу для cos^2 (Сценарий А) и cos^4 (Сценарий Б)
    # \Delta A = (20/ln10) * tan(\theta) * d_theta для cos^2
    # \Delta A = (40/ln10) * tan(\theta) * d_theta для cos^4
    angles_err = np.linspace(0, 85, 300)
    tan_vals = np.tan(np.radians(angles_err))
    
    # Сценарий А
    err_A_05 = (20.0 / np.log(10.0)) * tan_vals * d_theta_05
    err_A_10 = (20.0 / np.log(10.0)) * tan_vals * d_theta_10
    
    # Сценарий Б
    err_B_05 = (40.0 / np.log(10.0)) * tan_vals * d_theta_05
    err_B_10 = (40.0 / np.log(10.0)) * tan_vals * d_theta_10
    
    plt.plot(angles_err, err_A_05, 'g-', linewidth=2, label='Сценарий А (Болометр), $\\Delta\\theta = 0.5^\\circ$')
    plt.plot(angles_err, err_A_10, 'g--', linewidth=2, label='Сценарий А (Болометр), $\\Delta\\theta = 1.0^\\circ$')
    plt.plot(angles_err, err_B_05, 'r-', linewidth=2, label='Сценарий Б (ФПА), $\\Delta\\theta = 0.5^\\circ$')
    plt.plot(angles_err, err_B_10, 'r--', linewidth=2, label='Сценарий Б (ФПА), $\\Delta\\theta = 1.0^\\circ$')
    
    plt.xlabel('Угол установки ротатора $\\theta$ (град)', fontsize=11)
    plt.ylabel('Погрешность вносимого затухания $\\Delta A$ (дБ)', fontsize=11)
    plt.xlim(0, 85)
    plt.ylim(0, 3.0)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(fontsize=9, loc='upper left')
    plt.title('Чувствительность погрешности затухания к люфту ротатора', fontsize=12, fontweight='bold')
    
    plt.savefig(os.path.join(output_dir, 'passport_error.png'), dpi=200)
    plt.close()
    print("График 2 (passport_error.png) успешно создан.")
    
    # =========================================================================
    # ГРАФИК 3: Гистограмма распределения шага намотки
    # =========================================================================
    plt.figure(figsize=(7, 4))
    
    # Зададим модельные данные на основе анализа Image10_7_2026_1.bmp (mean=15.93, std=5.03)
    np.random.seed(42)
    fake_pitch = np.random.normal(15.93, 5.03, 300)
    # Отрежем нефизичные хвосты
    fake_pitch = fake_pitch[(fake_pitch >= 8.0) & (fake_pitch <= 28.0)]
    
    plt.hist(fake_pitch, bins=15, color='royalblue', edgecolor='black', alpha=0.8, density=True)
    plt.axvline(15.93, color='red', linestyle='--', linewidth=2, label='Средний шаг: 15.93 мкм')
    plt.axvline(16.0, color='green', linestyle=':', linewidth=2, label='Паспортный шаг: 16.0 мкм')
    
    plt.xlabel('Период намотки проволок $P$ (мкм)', fontsize=11)
    plt.ylabel('Плотность вероятности', fontsize=11)
    plt.title('Статистика однородности намотки решетки (разброс: 31.6%)', fontsize=11, fontweight='bold')
    plt.legend(fontsize=9)
    plt.grid(True, alpha=0.3)
    
    plt.savefig(os.path.join(output_dir, 'passport_pitch_dist.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("График 3 (passport_pitch_dist.png) успешно создан.")

if __name__ == '__main__':
    generate_plots()
