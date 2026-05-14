import threading
import serial
import serial.tools.list_ports
import queue
import time
from datetime import datetime

import wx
import wx.lib.newevent

SerialDataEvent, EVT_SERIAL_DATA = wx.lib.newevent.NewEvent()
SerialStatusEvent, EVT_SERIAL_STATUS = wx.lib.newevent.NewEvent()
ScriptDataEvent, EVT_SCRIPT_DATA = wx.lib.newevent.NewEvent()


class SerialWorker:
    def __init__(self, parent):
        self.serial = None
        self.rx_thread = None
        self.tx_thread = None
        self.rx_queue = queue.Queue()
        self.tx_queue = queue.Queue()
        self.running = False
        self.parent = parent

        self.auto_send_enabled = False
        self.auto_send_data = b''
        self.auto_send_interval = 1000
        self.auto_send_last = 0

        self.port_settings = {
            'port': '',
            'baudrate': 9600,
            'bytesize': serial.EIGHTBITS,
            'parity': serial.PARITY_NONE,
            'stopbits': serial.STOPBITS_ONE,
            'timeout': 0.1
        }

    @staticmethod
    def list_ports():
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    @staticmethod
    def list_baudrates():
        return [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 1152000]

    @staticmethod
    def list_parities():
        return [
            ('无', serial.PARITY_NONE),
            ('奇校验', serial.PARITY_ODD),
            ('偶校验', serial.PARITY_EVEN),
            ('标记', serial.PARITY_MARK),
            ('空格', serial.PARITY_SPACE)
        ]

    @staticmethod
    def list_stopbits():
        return [
            ('1', serial.STOPBITS_ONE),
            ('1.5', serial.STOPBITS_ONE_POINT_FIVE),
            ('2', serial.STOPBITS_TWO)
        ]

    def open_port(self, port, baudrate=9600, bytesize=serial.EIGHTBITS,
                  parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE):
        try:
            self.port_settings = {
                'port': port,
                'baudrate': baudrate,
                'bytesize': bytesize,
                'parity': parity,
                'stopbits': stopbits,
                'timeout': 0.1
            }

            self.serial = serial.Serial(**self.port_settings)
            self.running = True

            self.rx_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.tx_thread = threading.Thread(target=self._write_loop, daemon=True)
            self.rx_thread.start()
            self.tx_thread.start()

            self._post_status('connected', port=port, baudrate=baudrate)
            return True, f'成功打开串口 {port} ({baudrate}bps)'
        except Exception as e:
            return False, f'打开串口失败: {str(e)}'

    def close_port(self):
        self.running = False
        self.auto_send_enabled = False

        if self.rx_thread and self.rx_thread.is_alive():
            self.rx_thread.join(timeout=1)

        if self.tx_thread and self.tx_thread.is_alive():
            self.tx_thread.join(timeout=1)

        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception:
                pass

        self.serial = None
        self._post_status('disconnected')
        return True, '串口已关闭'

    def is_connected(self):
        return self.serial is not None and self.serial.is_open

    def send_data(self, data, is_hex=False, tag=''):
        if not self.is_connected():
            return False, '串口未连接'

        try:
            if is_hex:
                data_bytes = self._hex_str_to_bytes(data)
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                data_bytes = data.encode('utf-8')

            self.tx_queue.put(data_bytes)
            self._post_data('tx', data_bytes, tag)
            return True, '数据已发送'
        except Exception as e:
            return False, f'发送失败: {str(e)}'

    def set_auto_send(self, enabled, data=b'', interval_ms=1000, is_hex=False):
        try:
            if is_hex and isinstance(data, str):
                self.auto_send_data = self._hex_str_to_bytes(data)
            elif isinstance(data, str):
                self.auto_send_data = data.encode('utf-8')
            else:
                self.auto_send_data = bytes(data)
        except Exception as e:
            return False, f'数据格式错误: {str(e)}'

        self.auto_send_interval = max(10, interval_ms)
        self.auto_send_enabled = enabled
        self.auto_send_last = time.time() * 1000
        return True, '定时发送已更新'

    def _read_loop(self):
        while self.running and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    data = self.serial.read(self.serial.in_waiting)
                    self._post_data('rx', data)
                else:
                    time.sleep(0.01)
            except Exception as e:
                self._post_status('error', message=str(e))
                break

    def _write_loop(self):
        while self.running and self.serial and self.serial.is_open:
            try:
                now = time.time() * 1000
                if self.auto_send_enabled and self.auto_send_data:
                    if now - self.auto_send_last >= self.auto_send_interval:
                        self.tx_queue.put(self.auto_send_data)
                        self._post_data('tx', self.auto_send_data, 'auto')
                        self.auto_send_last = now

                if not self.tx_queue.empty():
                    data = self.tx_queue.get()
                    self.serial.write(data)
                else:
                    time.sleep(0.01)
            except Exception as e:
                self._post_status('error', message=str(e))
                break

    def _post_data(self, direction, data, tag=''):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        evt = SerialDataEvent(direction=direction, timestamp=timestamp, data=data, tag=tag)
        wx.PostEvent(self.parent, evt)

    def _post_status(self, status, **kwargs):
        evt = SerialStatusEvent(status=status, **kwargs)
        wx.PostEvent(self.parent, evt)

    def post_script_data(self, key, value):
        evt = ScriptDataEvent(key=key, value=value)
        wx.PostEvent(self.parent, evt)

    @staticmethod
    def _hex_str_to_bytes(hex_str):
        hex_str = ''.join(hex_str.split())
        if len(hex_str) % 2 != 0:
            hex_str = '0' + hex_str
        return bytes.fromhex(hex_str)

    @staticmethod
    def bytes_to_hex_str(data):
        return ' '.join(f'{b:02X}' for b in data)
