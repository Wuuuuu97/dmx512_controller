import time
import serial
from PyQt5.QtCore import QThread, pyqtSignal


class DMXTransmitter(QThread):
    """DMX512 protocol transmitter running in a dedicated thread.

    Continuously sends DMX frames at ~40+ fps:
      Break(100μs) + MAB(12μs) + StartCode(0x00) + 512 channel bytes

    Uses ``time.perf_counter()`` spin-wait for sub-millisecond timing
    to guarantee precision on Windows (where ``time.sleep()`` resolution
    is only ~15.6 ms by default).

    Error resilience: consecutive failures auto-stop to prevent infinite retry loops.

    Master fader & blackout: applied per-frame without modifying stored dmx_data.
    """
    status_changed = pyqtSignal(bool, str)  # (is_ok, message)

    # After this many consecutive send failures, auto-stop the thread
    _MAX_RETRIES = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dmx_data = bytearray(512)
        self._running = False
        self._serial = None
        self._serial_info = None  # port name string, saved for error messages
        self._master_level = 100   # 0-100, applied as percentage scale
        self._blackout = False     # True = send all zeros

    # ----------------------------------------------------------------
    # High-precision spin-wait (μs-level, OS-independent)
    # ----------------------------------------------------------------
    @staticmethod
    def _spin_sleep(seconds):
        """Busy-wait with ``time.perf_counter()`` for microsecond precision."""
        target = time.perf_counter() + seconds
        while time.perf_counter() < target:
            pass

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------
    def set_serial(self, serial_port):
        self._serial = serial_port
        self._serial_info = getattr(serial_port, "port", str(serial_port))

    def update_channel(self, channel, value):
        if 0 <= channel < 512:
            self.dmx_data[channel] = value & 0xFF

    def get_channel(self, channel):
        if 0 <= channel < 512:
            return self.dmx_data[channel]
        return 0

    def set_all_channels(self, data):
        if len(data) == 512:
            self.dmx_data = bytearray(data)

    def get_all_channels(self):
        return bytes(self.dmx_data)

    def reset_all(self):
        self.dmx_data = bytearray(512)

    def set_master_level(self, level):
        """Set master intensity level 0-100."""
        self._master_level = max(0, min(100, level))

    def set_blackout(self, active):
        """Enable/disable blackout (sends all zeros)."""
        self._blackout = active

    # ----------------------------------------------------------------
    # DMX frame transmission
    # ----------------------------------------------------------------
    def run(self):
        self._running = True
        fail_count = 0

        while self._running:
            if self._serial and self._serial.is_open:
                try:
                    # ---- DMX Break: ≥88μs logic 0 (space) ----
                    # Use break_condition + spin-wait for μs precision
                    self._serial.break_condition = True
                    self._spin_sleep(0.0001)          # 100 μs break
                    self._serial.break_condition = False

                    # ---- MAB (Mark After Break): ≥8μs logic 1 (mark) ----
                    self._spin_sleep(0.000012)        # 12 μs MAB

                    # ---- Build frame: Start Code (0x00) + 512 channel bytes ----
                    if self._blackout:
                        frame = bytes([0x00]) + bytes(512)
                    else:
                        raw = self.dmx_data
                        scale = self._master_level / 100.0
                        if scale >= 1.0:
                            frame = bytes([0x00]) + raw
                        elif scale <= 0.0:
                            frame = bytes([0x00]) + bytes(512)
                        else:
                            buf = bytearray(512)
                            for i in range(512):
                                buf[i] = int(raw[i] * scale)
                            frame = bytes([0x00]) + buf

                    self._serial.write(frame)
                    self._serial.flush()

                    fail_count = 0  # success — reset counter

                except (serial.SerialException, serial.SerialTimeoutException) as e:
                    fail_count += 1
                    err = str(e).lower()

                    if "write_timeout" in err or "timeout" in err:
                        msg = f"写入超时 ({self._serial_info}): {e}"
                    elif "access" in err or "permission" in err or "denied" in err:
                        msg = f"串口被占用 ({self._serial_info}): 请检查是否有其他程序在使用"
                    else:
                        msg = f"串口异常 ({self._serial_info}): {e}"

                    if fail_count >= self._MAX_RETRIES:
                        self.status_changed.emit(False, msg)
                        self._running = False
                        break
                    self._spin_sleep(0.020)

                except OSError as e:
                    win_err = getattr(e, "winerror", None)
                    if win_err == 1167:
                        msg = f"USB 设备已拔出 ({self._serial_info}) — 请检查连接"
                    elif win_err == 2:
                        msg = f"串口不存在 ({self._serial_info}) — 设备可能已拔出"
                    else:
                        msg = f"I/O 错误 ({self._serial_info}): {e}"

                    self.status_changed.emit(False, msg)
                    self._running = False
                    break

                except Exception as e:
                    self.status_changed.emit(False, f"未知错误: {e}")
                    self._running = False
                    break

            else:
                # No serial — idle loop
                self._spin_sleep(0.010)

            # MTBP (Mark Time Between Packets): 0-1 sec, using 5 ms
            self._spin_sleep(0.005)

    def stop(self):
        self._running = False
        self.wait(2000)
