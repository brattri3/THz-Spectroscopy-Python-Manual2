import config
from data_loader import load_dataset_to_store
from utils import get_signal_pair
from plots import plot_time_signals

def main():
    # 1. Инициализация базы данных в оперативной памяти
    db = load_dataset_to_store(config.DATA_DIR)
    
    # 2. Извлечение пары сигналов из базы данных (SQL-подобный запрос)
    t_bg, E_bg, t_sig, E_sig = get_signal_pair(db, angle1=50.0, angle2=0.0, rep=1)
    
    # 3. Визуализация извлеченной пары во временной области
    plot_time_signals(t_bg, E_bg, t_sig, E_sig)

if __name__ == "__main__":
    main()
