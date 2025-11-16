import threading
import time
import re

try:
    import serial  # pyserial
except ImportError as e:
    raise RuntimeError(
        "pyserial is required for receiver.py. "
        "Either install it or vendor the 'serial' module into your project."
    ) from e

# Adjust so it matches Arduino configuration
SERIAL_PORT = "COM6"      # e.g. "COM6" on Windows, "/dev/ttyACM0" on Linux
BAUD_RATE   = 9600        # must match Serial.begin(9600) on the Arduino
READ_TIMEOUT_S = 0.1      # non-blocking-ish

_ser = None
_started = False

_lock = threading.Lock()
_latest_raw_line = None          # raw text from Arduino (for debugging)
_latest_temp_c = None            # parsed numeric temperature
_latest_temp_line = None         # cleaned TEMP line for display

def _serial_reader():
    """Background thread: keep reading lines from the Arduino serial port."""
    global _latest_raw_line, _latest_temp_c, _latest_temp_line
    while True:
        try:
            line = _ser.readline()
        except Exception:
            time.sleep(0.1)
            continue

        if not line:
            time.sleep(0.01)
            continue

        try:
            text = line.decode("utf-8", errors="ignore").strip()
        except Exception:
            text = repr(line)

        with _lock:
            _latest_raw_line = text

            # Look for a TEMP:<number> pattern anywhere in the line,
            # e.g. "Received (ASCII): TEMP:23.5C  ###"
            m = re.search(r"TEMP:\s*([+-]?\d+(?:\.\d+)?)", text)
            if m:
                try:
                    val = float(m.group(1))
                except ValueError:
                    # shouldn't happen due to regex, but be safe
                    pass
                else:
                    _latest_temp_c = val
                    # Store a nice clean version for display (no garbage bytes)
                    _latest_temp_line = f"TEMP:{val:.2f}C"
                    print(f"[receiver] Parsed temperature: {_latest_temp_c} C from line: {text}")


def _ensure_started():
    global _ser, _started
    if _started:
        return
    _ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=READ_TIMEOUT_S)
    time.sleep(2.0)  # allow Arduino reset
    t = threading.Thread(target=_serial_reader, daemon=True)
    t.start()
    _started = True


def read_sensor_data():
    """
    Called by server.py once per second.
    Returns a dict merged into telemetry:
        {
            "temperature": <float or None>,
            "rfm_raw_data": "<clean TEMP line or last raw line>",
            "rfm_timestamp": <epoch seconds>,
        }
    """
    _ensure_started()
    with _lock:
        temp = _latest_temp_c
        # Prefer the cleaned TEMP line if we have one, otherwise last raw line
        raw_display = _latest_temp_line or _latest_raw_line

    return {
        "temperature": temp,
        "rfm_raw_data": raw_display,
        "rfm_timestamp": time.time(),
    }


def send_uplink_command(cmd: str):
    """
    Called by server.py when SAFE/SCIENCE/IDLE mode changes.
    Writes a line to Arduino serial, which the Arduino forwards via RFM69.
    """
    _ensure_started()
    line = cmd.strip() + "\n"
    try:
        _ser.write(line.encode("ascii"))
    except Exception as e:
        print("Failed to send uplink command:", e)


if __name__ == "__main__":
    while True:
        print(read_sensor_data())
        time.sleep(1.0)
