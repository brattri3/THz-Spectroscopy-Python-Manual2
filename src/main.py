import config
from data_loader import load_tds_data
from plots import plot_time_signals

def main():
    # 1. Загрузка экспериментальных данных
    t_sig, E_sig = load_tds_data(config.DATA_DIR / "50-0-1-bg_4.txt")
    t_bg, E_bg = load_tds_data(config.DATA_DIR / "bg_4.txt")
    
    # 2. Визуализация сигналов во временной области
    plot_time_signals(t_bg, E_bg, t_sig, E_sig)

if __name__ == "__main__":
    main()
