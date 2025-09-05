import logging
import time
import os
import pandas as pd
from ut61eplus import UT61EPLUS

# --- CONFIGURATION ---
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def example_single_measurement():
    """Example: connect, read a single measurement, and disconnect."""
    print("\n--- Example 1: Reading a single measurement ---")
    dmm = None
    try:
        dmm = UT61EPLUS()
        measurement = dmm.take_measurement()
        if measurement:
            data = measurement.to_dict()
            print("Data received:")
            print(data)
        else:
            print("Failed to get measurement.")
    except Exception as e:
        log.error(f"An error occurred: {e}")
    finally:
        if dmm:
            dmm.close()

def example_multiple_measurements(count=5):
    """Example: reading multiple measurements in a loop."""
    print(f"\n--- Example 2: Reading {count} measurements ---")
    dmm = None
    try:
        dmm = UT61EPLUS()
        for i in range(count):
            measurement = dmm.take_measurement()
            if measurement:
                print(f"Measurement {i+1}: {measurement.to_dict()}")
            else:
                print(f"Measurement {i+1}: Failed to get.")
            time.sleep(0.5) # A small pause between measurements
    except Exception as e:
        log.error(f"An error occurred: {e}")
    finally:
        if dmm:
            dmm.close()

def example_log_to_csv(duration_seconds=10):
    """Example: continuous logging of data to a CSV file for a specified duration."""
    print(f"\n--- Example 3: Logging to CSV for {duration_seconds} seconds ---")
    
    CSV_FILEPATH = "dmm_log.csv"
    BUFFER_SIZE = 50 # Write to file every 50 data points
    
    dmm = None
    data_buffer = []

    def write_buffer_to_csv():
        nonlocal data_buffer
        if not data_buffer:
            return
        
        df = pd.DataFrame(data_buffer)
        df.to_csv(CSV_FILEPATH, mode='a', header=not os.path.exists(CSV_FILEPATH), index=False)
        log.info(f"Wrote {len(data_buffer)} rows to {CSV_FILEPATH}")
        data_buffer = []

    try:
        dmm = UT61EPLUS()
        log.info(f"Starting data collection... Press Ctrl+C to stop.")
        
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
        log.error(f"An error occurred: {e}")
    finally:
        log.info("Shutting down, saving remaining buffer...")
        write_buffer_to_csv()
        if dmm:
            dmm.close()

def example_send_command():
    """Example: sending a command to toggle the backlight."""
    print("\n--- Example 4: Sending 'lamp' command ---")
    dmm = None
    try:
        dmm = UT61EPLUS()
        print("Turning on the backlight for 3 seconds...")
        dmm.send_command('lamp')
        time.sleep(3)
        
        print("Turning off the backlight.")
        dmm.send_command('lamp')
        time.sleep(1) # Pause to ensure the command has been sent
    except Exception as e:
        log.error(f"An error occurred: {e}")
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
