import config
import numpy as np
from data_loader import load_dataset_to_store
from utils import get_signal_pair
from plots import plot_time_signals

def main():
    # 1. Инициализация базы данных в оперативной памяти
    db = load_dataset_to_store(config.DATA_DIR)
    
    # 2. Ответ на мини-задание Раздела 4: Сравнение размаха при 0 и 90 градусах
    _, _, _, E_sig_0 = get_signal_pair(db, angle1=0.0, angle2=0.0, rep=1)
    _, _, _, E_sig_90 = get_signal_pair(db, angle1=90.0, angle2=0.0, rep=1)
    span_0 = np.max(E_sig_0) - np.min(E_sig_0)
    span_90 = np.max(E_sig_90) - np.min(E_sig_90)
    
    print("--- Решение мини-задания Раздела 4 ---")
    print(f"Размах сигнала при 0 градусах:  {span_0:.4f} у.е.")
    print(f"Размах сигнала при 90 градусах: {span_90:.4f} у.е.")
    print(f"Отношение амплитуд (0° / 90°):   {span_0 / span_90:.1f} раз")
    print("--------------------------------------\n")
    
    # 3. Извлечение пары сигналов из базы данных для угла 50 градусов (по тексту главы)
    t_bg, E_bg, t_sig, E_sig = get_signal_pair(db, angle1=50.0, angle2=0.0, rep=1)
    
    # 4. Визуализация извлеченной пары во временной области
    plot_time_signals(t_bg, E_bg, t_sig, E_sig)

if __name__ == "__main__":
    main()
