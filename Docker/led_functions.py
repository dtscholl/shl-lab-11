import os
import time
import threading

# Paths for BeagleBone Black LEDs
LED_PATHS = [
    "/sys/class/leds/beaglebone:green:usr0/brightness",
    "/sys/class/leds/beaglebone:green:usr1/brightness",
    "/sys/class/leds/beaglebone:green:usr2/brightness",
    "/sys/class/leds/beaglebone:green:usr3/brightness",
]

_current_mode = "IDLE"          # States: "IDLE", "SAFE", "SCIENCE"
_mode_lock = threading.Lock()
_thread_started = False


def set_led(index: int, on: bool):
    try:
        with open(LED_PATHS[index], "w") as f:
            f.write("1" if on else "0")
    except Exception:
        # Ignore errors if some LEDs don't exist on this board
        pass


def set_all(on: bool):
    for i in range(4):
        set_led(i, on)


def set_mode(mode: str):
    """Change the LED mode: 'IDLE', 'SAFE', or 'SCIENCE'."""
    global _current_mode
    mode = mode.upper()
    if mode not in ("IDLE", "SAFE", "SCIENCE"):
        return
    with _mode_lock:
        _current_mode = mode
    print(f"[LED] Mode set to: {_current_mode}")


def _led_controller():
    """Background thread: animates LEDs based on _current_mode."""
    index = 0
    while True:
        with _mode_lock:
            mode = _current_mode

        if mode == "IDLE":
            # All off
            set_all(False)
            time.sleep(0.1)

        elif mode == "SAFE":
            # All blink together with a 3 s period (1.5 on, 1.5 off)
            set_all(True)
            time.sleep(1.5)
            set_all(False)
            time.sleep(1.5)

        elif mode == "SCIENCE":
            # Fast cycling: one LED at a time, rotating
            set_all(False)
            set_led(index, True)
            index = (index + 1) % 4
            time.sleep(0.15)


def start_led_controller():
    """Start the LED controller thread once."""
    global _thread_started
    if _thread_started:
        return
    t = threading.Thread(target=_led_controller, daemon=True)
    t.start()
    _thread_started = True
    print("[LED] Controller thread started")
