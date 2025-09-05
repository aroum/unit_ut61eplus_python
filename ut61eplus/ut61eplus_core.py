import decimal
import logging
import time
import hid

log = logging.getLogger(__name__)

class Measurement:
    """Class for storing and decoding a single measurement from the multimeter."""
    _MODE = ['ACV', 'ACmV', 'DCV', 'DCmV', 'Hz', '%', 'OHM', 'CONT', 'DIDOE', 'CAP', '°C', '°F', 'DCuA', 'ACuA', 'DCmA',
             'ACmA', 'DCA', 'ACA', 'HFE', 'Live', 'NCV', 'LozV', 'ACA', 'DCA', 'LPF', 'AC/DC', 'LPF', 'AC+DC', 'LPF',
             'AC+DC2', 'INRUSH']
    _UNITS = {'%': {'0': '%'}, 'AC+DC': {'1': 'A'}, 'AC+DC2': {'1': 'A'},
              'AC/DC': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'ACA': {'1': 'A'}, 'ACV': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'}, 'ACmA': {'0': 'mA', '1': 'mA'},
              'ACmV': {'0': 'mV'}, 'ACuA': {'0': 'uA', '1': 'uA'},
              'CAP': {'0': 'nF', '1': 'nF', '2': 'uF', '3': 'uF', '4': 'uF', '5': 'mF', '6': 'mF', '7': 'mF'},
              'CONT': {'0': 'Ω'}, 'DCA': {'1': 'A'}, 'DCV': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'DCmA': {'0': 'mA', '1': 'mA'}, 'DCmV': {'0': 'mV'}, 'DCuA': {'0': 'uA', '1': 'uA'}, 'DIDOE': {'0': 'V'},
              'Hz': {'0': 'Hz', '1': 'Hz', '2': 'kHz', '3': 'kHz', '4': 'kHz', '5': 'MHz', '6': 'MHz', '7': 'MHz'},
              'LPF': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'}, 'LozV': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'OHM': {'0': 'Ω', '1': 'kΩ', '2': 'kΩ', '3': 'kΩ', '4': 'MΩ', '5': 'MΩ', '6': 'MΩ'},
              '°C': {'0': '°C', '1': '°C'}, '°F': {'0': '°F', '1': '°F'}, 'HFE': {'0': 'B'}, 'NCV': {'0': 'NCV'}}
    _OVERLOAD = {'.OL', 'O.L', 'OL.', 'OL', '-.OL', '-O.L', '-OL.', '-OL'}
    _EXPONENTS = {'M': 6, 'k': 3, 'm': -3, 'u': -6, 'n': -9}

    def __init__(self, b: bytes):
        if not isinstance(b, bytes) or len(b) < 14:
            raise TypeError("Measurement requires a minimum of 14 bytes for initialization.")
        
        self.raw_bytes = b
        self.mode = self._MODE[b[0]]
        self.range_char = chr(b[1])
        self.display = b[2:9].decode('ASCII', errors='ignore').replace(' ', '')
        self.is_overload = self.display in self._OVERLOAD
        
        # Main flags
        self.is_max = (b[11] & 8) > 0
        self.is_min = (b[11] & 4) > 0
        self.is_hold = (b[11] & 2) > 0
        self.is_rel = (b[11] & 1) > 0
        self.is_auto_range = (b[12] & 4) == 0
        self.has_battery_warning = (b[12] & 2) > 0
        self.has_hv_warning = (b[12] & 1) > 0
        self.is_max_peak = (b[13] & 4) > 0
        self.is_min_peak = (b[13] & 2) > 0
        
        try:
            self.decimal_value = decimal.Decimal(self.display)
        except decimal.InvalidOperation:
            self.decimal_value = decimal.Decimal('NaN')

        self.display_unit = self._UNITS.get(self.mode, {}).get(self.range_char)
        self.unit = self.display_unit

        if self.unit and len(self.unit) > 0 and self.unit[0] in self._EXPONENTS and not self.is_overload:
            self.decimal_value = self.decimal_value.scaleb(self._EXPONENTS[self.unit[0]])
            self.unit = self.unit[1:]

    def to_dict(self):
        """Returns all measurement data in the requested dictionary format."""
        min_max_status = None
        if self.is_max: min_max_status = 'max'
        elif self.is_min: min_max_status = 'min'
        elif self.is_max_peak: min_max_status = 'p-max'
        elif self.is_min_peak: min_max_status = 'p-min'
        
        val = self.decimal_value
        return {
            'value': float(val) if not self.is_overload and not val.is_nan() else 0.0,
            'unit': self.unit,
            'mode': self.mode,
            'range': 'AUTO' if self.is_auto_range else 'MANUAL',
            'overload': self.is_overload,
            'hold': self.is_hold,
            'min_max': min_max_status,
            'rel': self.is_rel,
            'hv_warning': self.has_hv_warning,
            'bat_low': self.has_battery_warning
        }

class UT61EPLUS:
    CP2110_VID = 0x10c4
    CP2110_PID = 0xEA80
    _SEQUENCE_SEND_DATA = bytes.fromhex('AB CD 03 5E 01 D9')
    _SEQUENCE_SEND_CMD = bytes.fromhex('AB CD 03')
    _COMMANDS = {
        'min_max': 65, 'not_min_max': 66, 'range': 70, 'auto': 71, 'rel': 72, 
        'select2': 73, 'hold': 74, 'lamp': 75, 'select1': 76, 'p_min_max': 77, 'not_peak': 78
    }

    def __init__(self):
        log.info('Connecting to UT61E+...')
        self.dev = hid.device()
        self.dev.open(self.CP2110_VID, self.CP2110_PID)
        self.dev.send_feature_report([0x41, 0x01])
        self.dev.send_feature_report([0x50, 0x00, 0x00, 0x25, 0x80, 0x00, 0x00, 0x03, 0x00, 0x00])
        self.dev.send_feature_report([0x43, 0x02])
        log.info('Device successfully configured.')
        self.read_buffer = bytearray()

    def _write(self, b: bytes):
        self.dev.write(bytearray([len(b)]) + b)

    def _read_packet(self, timeout=1.0) -> bytes:
        timeout_start = time.time()
        while time.time() - timeout_start < timeout:
            start_index = self.read_buffer.find(b'\xab\xcd')
            if start_index != -1 and len(self.read_buffer) > start_index + 2:
                payload_len = self.read_buffer[start_index + 2]
                full_packet_len = 3 + payload_len
                if len(self.read_buffer) >= start_index + full_packet_len:
                    packet = self.read_buffer[start_index: start_index + full_packet_len]
                    self.read_buffer = self.read_buffer[start_index + full_packet_len:]
                    if sum(packet[:-2]) == (packet[-2] << 8) + packet[-1]: return bytes(packet[3:])
                    log.warning("Checksum error! Packet discarded.")
                    continue
            raw = self.dev.read(64, 10) # Optimized timeout
            if raw: self.read_buffer.extend(bytes(raw[1:2]))
        return None

    def take_measurement(self):
        self._write(self._SEQUENCE_SEND_DATA)
        payload = self._read_packet()
        return Measurement(payload[:-2]) if payload and len(payload) == 16 else None

    def send_command(self, cmd) -> None:
        """Sends a command to the device."""
        cmd_code = self._COMMANDS.get(cmd) if isinstance(cmd, str) else cmd
        if not isinstance(cmd_code, int):
            raise ValueError(f'Invalid command: {cmd}')

        seq = bytearray(self._SEQUENCE_SEND_CMD)
        checksum = cmd_code + 379
        seq.extend([cmd_code, checksum >> 8, checksum & 0xff])
        
        log.info(f"Sending command: '{cmd}' (code: {cmd_code})")
        self._write(seq)
        # After a command, the device might send a response packet, which needs to be "absorbed"
        self._read_packet(timeout=0.2) 

    def close(self):
        self.dev.close()
        log.info("Connection to device closed.")

def data_collector(dmm, data_queue, stop_event):
    """This function runs in a separate thread and only collects data."""
    log.info("Data collection thread started.")
    while not stop_event.is_set():
        measurement = dmm.take_measurement()
        if measurement:
            data_queue.put(measurement.to_dict())
    log.info("Data collection thread stopped.")
