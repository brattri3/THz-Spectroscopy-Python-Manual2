from pathlib import Path

# --- ПУТИ К ДАННЫМ ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# --- ПАРАМЕТРЫ ЦИФРОВОЙ ОБРАБОТКИ (DSP) ---
SIGMA_PS = 20.0
F_MIN = 0.1
F_MAX = 2.0

# --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ ПОЛЯРИЗАТОРА (Теория Бланко) ---
P_DEFAULT = 16.0e-6         # Паспортный шаг решетки (м)
D_DEFAULT = 11.0e-6         # Паспортный диаметр проволоки (м)
PERIOD_SCALE_DEFAULT = 1.0  # Масштабный множитель периода
LOSS_FACTOR_DEFAULT = 0.0   # Коэффициент потерь

if __name__ == '__main__':
    print("Конфигурация проекта успешно загружена!")
    print(f"Путь к данным: {DATA_DIR}")
