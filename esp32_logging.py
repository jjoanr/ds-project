import os
import serial
import threading
import re
import csv
from datetime import datetime

# Regex
log_pattern = re.compile(r"Received from ([0-9a-f:]+).*Ratio ([0-9.]+)")

def serial_log(port):
    ser = serial.Serial(port)
    filename = f"log_{port.replace('/', '_')}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "port", "mac", "ratio"])
        while True:
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                match = log_pattern.search(line)
                if match:
                    mac = match.group(1)
                    ratio = float(match.group(2))
                    timestamp = datetime.now().isoformat()

                    writer.writerow([timestamp, port, mac, ratio])
                    f.flush()

                    print(f"{port} | {mac} | {ratio}")

            except Exception as e:
                print(f"Error on {port}: {e}")
                break

    ser.close()

esp32_ports = [
    "/dev/ttyUSB1",
    "/dev/ttyUSB2",
    "/dev/ttyUSB3",
    "/dev/ttyUSB4",
]

# Each thread monitors a serial port for incomming esp32 data, saving to a csv
threads = []

for port in esp32_ports:
    t = threading.Thread(target=serial_log, args=(port,))
    t.daemon = True
    threads.append(t)

for t in threads:
    t.start()

for t in threads:
    t.join()
