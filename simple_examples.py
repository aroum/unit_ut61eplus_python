import logging
import time
import os
import pandas as pd
from ut61eplus import UT61EPLUS
from ut61eplus import data_collector

# --- НАСТРОЙКА ---
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def example_single_measurement():
    """Пример: подключиться, прочитать одно измерение и отключиться."""
    print("\n--- Пример 1: Чтение одного измерения ---")
    dmm = None
    try:
        dmm = UT61EPLUS()
        measurement = dmm.take_measurement()
        if measurement:
            data = measurement.to_dict()
            print("Получены данные:")
            print(data)
        else:
            print("Не удалось получить измерение.")
    except Exception as e:
        log.error(f"Произошла ошибка: {e}")
    finally:
        if dmm:
            dmm.close()

def example_multiple_measurements(count=5):
    """Пример: чтение нескольких измерений в цикле."""
    print(f"\n--- Пример 2: Чтение {count} измерений ---")
    dmm = None
    try:
        dmm = UT61EPLUS()
        for i in range(count):
            measurement = dmm.take_measurement()
            if measurement:
                print(f"Измерение {i+1}: {measurement.to_dict()}")
            else:
                print(f"Измерение {i+1}: Не удалось получить.")
            time.sleep(0.5) # Небольшая пауза между измерениями
    except Exception as e:
        log.error(f"Произошла ошибка: {e}")
    finally:
        if dmm:
            dmm.close()

def example_log_to_csv(duration_seconds=10):
    """Пример: непрерывная запись данных в CSV файл в течение заданного времени."""
    print(f"\n--- Пример 3: Запись в CSV в течение {duration_seconds} секунд ---")
    
    CSV_FILEPATH = "dmm_log.csv"
    BUFFER_SIZE = 50 # Записывать в файл каждые 50 точек
    
    dmm = None
    data_buffer = []

    def write_buffer_to_csv():
        nonlocal data_buffer
        if not data_buffer:
            return
        
        df = pd.DataFrame(data_buffer)
        df.to_csv(CSV_FILEPATH, mode='a', header=not os.path.exists(CSV_FILEPATH), index=False)
        log.info(f"Записано {len(data_buffer)} строк в {CSV_FILEPATH}")
        data_buffer = []

    try:
        dmm = UT61EPLUS()
        log.info(f"Начинаю сбор данных... Нажмите Ctrl+C для остановки.")
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            try:
                measurement = dmm.take_measurement()
                if measurement:
                    data_buffer.append(measurement.to_dict())
                
                if len(data_buffer) >= BUFFER_SIZE:
                    write_buffer_to_csv()
            except KeyboardInterrupt:
                break
    
    except Exception as e:
        log.error(f"Произошла ошибка: {e}")
    finally:
        log.info("Завершение работы, сохраняю остатки буфера...")
        write_buffer_to_csv()
        if dmm:
            dmm.close()

def example_send_command():
    """Пример: отправка команды для включения/выключения подсветки."""
    print("\n--- Пример 4: Отправка команды 'lamp' ---")
    dmm = None
    try:
        dmm = UT61EPLUS()
        print("Включаю подсветку на 3 секунды...")
        dmm.send_command('lamp')
        time.sleep(3)
        
        print("Выключаю подсветку.")
        dmm.send_command('lamp')
        time.sleep(1) # Пауза чтобы убедиться что команда прошла
    except Exception as e:
        log.error(f"Произошла ошибка: {e}")
    finally:
        if dmm:
            dmm.close()


if __name__ == '__main__':
    example_single_measurement()
    time.sleep(2)
    example_multiple_measurements()
    time.sleep(2)
    example_log_to_csv(duration_seconds=5)
    time.sleep(2)
    example_send_command()


