import logging
import queue
import threading
import time
from collections import deque
import hid
import matplotlib.animation as animation
import matplotlib.pyplot as plt

from ut61eplus import UT61EPLUS, data_collector


# --- НАСТРОЙКА ---
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
MAX_PLOT_POINTS = 100
GUI_UPDATE_INTERVAL_MS = 100

# --- Основной код ---
dmm = None
data_collector_thread = None

try:
    dmm = UT61EPLUS()
    data_queue = queue.Queue()
    stop_event = threading.Event()

    data_collector_thread = threading.Thread(target=data_collector, args=(dmm, data_queue, stop_event))
    data_collector_thread.start()

    x_data, y_data = deque(maxlen=MAX_PLOT_POINTS), deque(maxlen=MAX_PLOT_POINTS)
    fig, ax = plt.subplots()
    line, = ax.plot([], [], 'r-')
    ax.set_xlabel("Время")
    ax.grid(True)
    fig.canvas.manager.set_window_title('UT61E+ Real-Time Data')

    last_time = time.time(); sample_count = 0; rate = 0
    
    # Эта переменная будет хранить последние данные для обновления заголовка
    last_data = {}

    def update(frame):
        global last_time, sample_count, rate, last_data

        points_processed = 0
        while not data_queue.empty():
            data = data_queue.get()
            last_data = data # Сохраняем последние данные
            y_data.append(data['value'] if not data['overload'] else 0)
            x_data.append(time.time())
            points_processed += 1

        if points_processed > 0:
            sample_count += points_processed
            current_time = time.time()
            if current_time - last_time >= 1.0:
                rate = sample_count / (current_time - last_time)
                sample_count = 0; last_time = current_time

            line.set_data(x_data, y_data)
            ax.relim(); ax.autoscale_view()
            
            # Используем новые ключи из словаря
            status_hold = "HOLD" if last_data.get('hold') else "Live"
            status_range = last_data.get('range', 'N/A')
            title = f"Режим: {last_data.get('mode')} ({status_range}) | {status_hold} | Скорость: {rate:.1f} изм/с"
            ax.set_title(title, fontsize=12)
            ax.set_ylabel(f"Значение ({last_data.get('unit') or 'N/A'})")
            fig.tight_layout()

        return line,

    ani = animation.FuncAnimation(fig, update, blit=False, interval=GUI_UPDATE_INTERVAL_MS, save_count=0)
    plt.show()

except hid.HIDException as e: log.error(f"Ошибка HID: {e}")
except KeyboardInterrupt: log.info("Программа остановлена.")
except Exception: log.error("Непредвиденная ошибка:", exc_info=True)
finally:
    if data_collector_thread:
        stop_event.set()
        data_collector_thread.join()
    if dmm: dmm.close()

