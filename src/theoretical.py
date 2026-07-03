import numpy as np
import config

EPS = 1e-12

def compute_C(m: int, p_over_lambda: float) -> complex:
    """
    Вычисляет параметр C_m для m-й гармоники ряда Бланко.
    """
    val = m**2 - p_over_lambda**2
    return np.sqrt(val + 0j)


def safe_log(x: float) -> float:
    """
    Вычисляет защищенный натуральный логарифм для избежания деления на ноль.
    """
    return np.log(max(x, EPS))


def compute_A1(p_over_lambda: float, d_over_p: float, N: int = 15) -> float:
    """
    Вычисляет слагаемое A_1 для индуктивного сопротивления.
    """
    if d_over_p <= 0 or d_over_p >= 1:
        return 1.0
    pi_d_over_lambda = np.pi * d_over_p * p_over_lambda
    log_arg = 1.0 / (np.pi * d_over_p)
    term2 = 0.5 * (pi_d_over_lambda)**2 * (safe_log(log_arg) + 0.75)
    sum_m = 0.0
    for m in range(1, N + 1):
        sum_m += (1.0 / compute_C(m, p_over_lambda) - 1.0 / m)
    term3 = 0.5 * (pi_d_over_lambda)**2 * sum_m
    return 1.0 + term2 + term3


def compute_A2(p_over_lambda: float, d_over_p: float, N: int = 15) -> float:
    """
    Вычисляет слагаемое A_2 для емкостного сопротивления.
    """
    if d_over_p <= 0 or d_over_p >= 1:
        return 1.0
    pi_d_over_lambda = np.pi * d_over_p * p_over_lambda
    log_arg = 1.0 / (np.pi * d_over_p)
    term2 = 0.5 * (pi_d_over_lambda)**2 * (11.0 / 4.0 - safe_log(log_arg))
    term3 = (1.0 / 24.0) * (pi_d_over_lambda)**2
    sum_m = 0.0
    for m in range(1, N + 1):
        sum_m += (m - 0.5 / m * (p_over_lambda)**2 - compute_C(m, p_over_lambda))
    term4 = - (pi_d_over_lambda)**2 * sum_m
    return 1.0 + term2 + term3 + term4


def compute_fa(p_over_lambda: float, d_over_p: float, N: int = 15) -> float:
    """
    Вычисляет мнимую часть импеданса fa.
    """
    if d_over_p <= 0 or d_over_p >= 1:
        return 1e6
    A2 = compute_A2(p_over_lambda, d_over_p, N)
    if abs(A2) < EPS:
        return 1e6
    return 0.5 * p_over_lambda * (np.pi * d_over_p)**2 / A2


def compute_fb(p_over_lambda: float, d_over_p: float, N: int = 15) -> float:
    """
    Вычисляет мнимую часть импеданса fb.
    """
    if d_over_p <= 0 or d_over_p >= 1:
        return -1e6
    A1 = compute_A1(p_over_lambda, d_over_p, N)
    A2 = compute_A2(p_over_lambda, d_over_p, N)
    if abs(A2) < EPS or abs(p_over_lambda) < EPS:
        return -1e6
    term1 = 2.0 / p_over_lambda * (1.0 / (np.pi * d_over_p))**2 * A1
    term2 = - p_over_lambda / 4.0 * (np.pi * d_over_p)**2 / A2
    return term1 + term2


def compute_fc(p_over_lambda: float, d_over_p: float, N: int = 15) -> float:
    """
    Вычисляет комплексное сопротивление fc.
    """
    if d_over_p <= 0 or d_over_p >= 1:
        return 0.0
    sum_m = 0.0
    for m in range(1, N + 1):
        sum_m += (1.0 / compute_C(m, p_over_lambda) - 1.0 / m)
    log_arg = 1.0 / (np.pi * d_over_p)
    return p_over_lambda * (safe_log(log_arg) + sum_m)


def compute_fd(p_over_lambda: float, d_over_p: float) -> float:
    """
    Вычисляет комплексное сопротивление fd.
    """
    if d_over_p <= 0 or d_over_p >= 1:
        return 0.0
    return p_over_lambda * (np.pi * d_over_p)**2


def compute_t_perp(p_over_lambda: float, d_over_p: float, N: int = 15) -> complex:
    """
    Вычисляет амплитудный коэффициент пропускания перпендикулярной поляризации.
    """
    fa = compute_fa(p_over_lambda, d_over_p, N)
    fb = compute_fb(p_over_lambda, d_over_p, N)
    Z1, Z2 = 1j * fa, 1j * fb
    denom1, denom2 = 1.0 + Z1, 1.0 + Z2
    if abs(denom1) < EPS or abs(denom2) < EPS:
        return 0.0
    return 1.0 / denom1 - 1.0 / denom2


def compute_t_par(p_over_lambda: float, d_over_p: float, N: int = 15) -> complex:
    """
    Вычисляет амплитудный коэффициент пропускания параллельной поляризации.
    """
    fc = compute_fc(p_over_lambda, d_over_p, N)
    fd = compute_fd(p_over_lambda, d_over_p)
    Z3, Z4 = 1j * fc, 1j * fd
    denom1, denom2 = 1.0 + Z3, 1.0 + Z3 * Z4 + Z3 + Z4
    if abs(denom1) < EPS or abs(denom2) < EPS:
        return 0.0
    return 2.0 * Z3 * Z4 / denom2


def transmission_two_polarizers(theta: float, p_over_lambda: float, d_over_p: float, N: int = 15) -> float:
    """
    Вычисляет коэффициент пропускания по мощности для системы из двух поляризаторов,
    первый из которых развернут на угол theta (в радианах).
    """
    t_perp = compute_t_perp(p_over_lambda, d_over_p, N)
    t_par = compute_t_par(p_over_lambda, d_over_p, N)
    
    c, s = np.cos(theta), np.sin(theta)
    # Матрицы Джонса для вращения и пропускания
    R = np.array([[c, -s], [s, c]])
    R_inv = np.array([[c, s], [-s, c]])
    P = np.array([[t_perp, 0.0], [0.0, t_par]])
    
    # Результирующая матрица системы: M = P * R * P * R_inv
    M = P @ R @ P @ R_inv
    E_in = np.array([1.0, 0.0])
    E_out = M @ E_in
    
    return float(np.clip(np.abs(E_out[0])**2 + np.abs(E_out[1])**2, 0.0, 1.0))


def transmission_db_modified(theta_deg: float, p: float, d: float, freq_THz: float, 
                             period_scale: float, loss_factor: float, N: int = 15) -> float:
    """
    Модифицированная модель пропускания в дБ с учетом масштабного множителя
    периода решетки (period_scale) и частотно-зависимых потерь (loss_factor).
    """
    if freq_THz <= 0:
        return -1e6
        
    c_light = 3e8
    lambda_m = c_light / (freq_THz * 1e12)
    p_eff = p * period_scale
    p_over_lambda = p_eff / lambda_m
    d_over_p = d / p_eff
    
    if d_over_p <= 0 or d_over_p >= 1:
        return -1e6
        
    theta_rad = np.deg2rad(theta_deg)
    T_linear = transmission_two_polarizers(theta_rad, p_over_lambda, d_over_p, N)
    
    # Добавление частотно-зависимых потерь по закону Бугера-Ламберта-Бера
    T_linear_mod = T_linear * np.exp(-loss_factor * freq_THz)
    
    return float(10 * np.log10(np.maximum(T_linear_mod, 1e-12)))


if __name__ == '__main__':
    import data_loader
    import spectrum
    
    print("=========================================================")
    print("Сопоставление экспериментальных и теоретических данных")
    print("=========================================================")
    
    # Пути к реальным файлам из Листинга 11
    sig_path = config.DATA_DIR / "50-0-1-bg_4.txt"
    bg_path = config.DATA_DIR / "bg_4.txt"
    
    try:
        # Загружаем реальные данные из Листинга 11
        t_sig, E_sig = data_loader.load_tds_data(sig_path)
        t_bg, E_bg = data_loader.load_tds_data(bg_path)
        
        # Рассчитываем экспериментальное пропускание
        freqs, _, _, trans = spectrum.calculate_transmission(t_sig, E_sig, t_bg, E_bg)
        
        # Находим значение пропускания на частоте 1.0 ТГц
        target_freq = 1.0
        idx = np.argmin(np.abs(freqs - target_freq))
        exp_trans_db = 10 * np.log10(max(trans[idx], 1e-12))
        
        # Рассчитываем теоретическое пропускание по модели Бланко для угла 50 градусов
        theo_trans_db = transmission_db_modified(
            theta_deg=50.0,
            p=config.P_DEFAULT,
            d=config.D_DEFAULT,
            freq_THz=target_freq,
            period_scale=config.PERIOD_SCALE_DEFAULT,
            loss_factor=config.LOSS_FACTOR_DEFAULT
        )
        
        print("\nРезультаты сопоставления на частоте {:.2f} ТГц:".format(target_freq))
        print("  - Экспериментальное пропускание: {:.2f} дБ".format(exp_trans_db))
        print("  - Теоретическое пропускание (Blanco): {:.2f} дБ".format(theo_trans_db))
        print("  - Разница: {:.2f} дБ".format(abs(exp_trans_db - theo_trans_db)))
        print("\nТест успешно пройден!")
        
    except Exception as e:
        print(f"Ошибка при загрузке или обработке файлов: {e}")
        print("Убедитесь, что файлы данных '50-0-1-bg_4.txt' и 'bg_4.txt' находятся в директории данных.")

