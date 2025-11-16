# Simple example to send a message and then wait indefinitely for messages
# to be received.  This uses the default RadioHead compatible GFSK_Rb250_Fd250
# modulation and packet format for the radio.

import board
import busio
import digitalio
import time

import adafruit_rfm69
import led_functions as led
import temp_sim as tmp

# Define radio parameters.
RADIO_FREQ_MHZ = 915.0  # Frequency of the radio in MHz

# Define pins connected to the chip, use these if wiring up the breakout according to the guide:
CS = digitalio.DigitalInOut(board.P9_17)
RESET = digitalio.DigitalInOut(board.P9_12)

# Initialize SPI bus.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialze RFM radio
rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, RADIO_FREQ_MHZ)

# Optionally set an encryption key (16 byte AES key). MUST match both
# on the transmitter and receiver (or be set to None to disable/the default).
rfm69.encryption_key = b"\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08"

# Print out some chip state:
print(f"Temperature: {rfm69.temperature}C")
print(f"Frequency: {rfm69.frequency_mhz}mhz")
print(f"Bit rate: {rfm69.bitrate / 1000}kbit/s")
print(f"Frequency deviation: {rfm69.frequency_deviation}hz")

print("Waiting for packets...")

# Start LED controller thread (IDLE by default)
led.start_led_controller()
led.set_mode("IDLE")

last_temp_sent = 0.0
TEMP_PERIOD = 5.0

while True:
    packet = rfm69.receive(timeout=10.0)
    if packet is None:
        print("Received nothing! Listening again...")
    else:
        print(f"Received (raw bytes): {packet}")
        try:
            packet_text = packet.decode("ascii", errors="ignore").strip()
        except Exception:
            packet_text = str(packet)
        print(f"Received (ASCII): {packet_text}")

        # Interpret packet_text as a CubeSat mode command
        if packet_text in ("SAFE", "SCIENCE", "IDLE"):
            led.set_mode(packet_text)
            print(f"LED mode changed to: {packet_text}")
        else:
            # Other telemetry/data messages can be handled here
            pass

    # After handling commands, send current temperature to Arduino
    now = time.monotonic()
    if now - last_temp_sent >= TEMP_PERIOD:
        temp_c = tmp.read_temp_data()["temperature"]
        temp_msg = f"TEMP:{temp_c:.2f}"
        rfm69.send(temp_msg.encode("ascii"))
        print("Sent temperature:", temp_msg)
        last_temp_sent = now