#!/usr/bin/env python3
import serial
import threading
import re
import time
import numpy as np
import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
ESP32_PORTS     = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2", "/dev/ttyUSB3"]
BAUD_RATE       = 115200
TOLERANCE       = 1e-4
REQUIRED_STABLE = 5
BOOT_WAIT       = 28
CHECK_INTERVAL  = 1.0
NUM_RUNS        = 20
INTER_RUN_DELAY = 5

PACKET_LOSS_PCT = 0.0 

OUTPUT_DIR = Path("logs")
OUTPUT_DIR.mkdir(exist_ok=True)
SUMMARY_FILE = OUTPUT_DIR / "naive_summary_0_loss.csv"

# Regex for parsing
INIT_RE   = re.compile(r"INIT_STATE MAC=([0-9a-f:]+) VAL=([0-9.]+) WEIGHT=([0-9.]+)")
STATUS_RE = re.compile(r"STATUS MAC=([0-9a-f:]+) RATIO=([0-9.]+) VAL=([0-9.]+) W=([0-9.]+)")

def reset_boards() -> None:
    print("\n[reset] Resetting all boards via esptool...")
    def _reset_one(port):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "esptool", "--port", port, "--chip", "esp32",
                 "--after", "hard-reset", "read_mac"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print(f"  [reset] {port} OK")
            else:
                print(f"  [reset] {port} FAILED:\n{result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"  [reset] {port} timed out")
        except Exception as e:
            print(f"  [reset] {port} error: {e}")

    threads = [threading.Thread(target=_reset_one, args=(p,)) for p in ESP32_PORTS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("[reset] Done reseting.")


def run_single_experiment(run_idx: int, raw_writer, raw_file) -> dict | None:
    state = {
        "initial_values": {},
        "latest_ratios":  {},
        "latest_values":  {},
        "latest_weights": {},
        "tx_counts":      {},
    }
    lock = threading.Lock()
    stop_event = threading.Event()

    def monitor(port):
        try:
            ser = serial.Serial(port, BAUD_RATE, timeout=2)
            while not stop_event.is_set():
                try:
                    line = ser.readline().decode(errors="ignore").strip()
                except Exception:
                    break
                if not line:
                    continue

                m = INIT_RE.search(line)
                if m:
                    mac, val, w = m.groups()
                    with lock:
                        state["initial_values"][mac] = float(val)
                    raw_writer.writerow([
                        datetime.now().isoformat(), run_idx, port,
                        mac, "INIT", val, w, ""
                    ])
                    raw_file.flush()
                    print(f"[{port}] INIT  {mac}  val={val}")
                    continue

                m = STATUS_RE.search(line)
                if m:
                    mac, ratio, val, w = m.groups()
                    with lock:
                        state["latest_ratios"][mac] = float(ratio)
                        state["latest_values"][mac] = float(val)
                        state["latest_weights"][mac] = float(w)
                        state["tx_counts"][mac] = state["tx_counts"].get(mac, 0) + 1
                    raw_writer.writerow([
                        datetime.now().isoformat(), run_idx, port,
                        mac, "STATUS", val, w, ratio
                    ])
            ser.close()
        except Exception as e:
            print(f"[{port}] ERROR: {e}")

    threads = [
        threading.Thread(target=monitor, args=(p,), daemon=True)
        for p in ESP32_PORTS
    ]
    for t in threads:
        t.start()

    # Wait for INIT from all boards
    deadline = time.time() + BOOT_WAIT
    while time.time() < deadline:
        with lock:
            n = len(state["initial_values"])
        if n == len(ESP32_PORTS):
            break
        time.sleep(0.5)

    with lock:
        n_init = len(state["initial_values"])

    if n_init != len(ESP32_PORTS):
        print(f"[run {run_idx}] ERROR: only received INIT from {n_init}/{len(ESP32_PORTS)} boards — aborting run")
        stop_event.set()
        return None

    with lock:
        true_mean = float(np.mean(list(state["initial_values"].values())))
        initial_mass = float(np.sum(list(state["initial_values"].values())))

    print(f"  All boards initialised. True mean={true_mean:.4f}  mass={initial_mass:.4f}")

    # Convergence check loop
    stability_counter = 0
    start_time = time.time()

    while True:
        time.sleep(CHECK_INTERVAL)

        with lock:
            if len(state["latest_ratios"]) < len(ESP32_PORTS):
                continue   # not everyone has sent a status yet

            ratios = np.array(list(state["latest_ratios"].values()))
            current_mass = float(np.sum(list(state["latest_values"].values())))
            current_mean = float(np.mean(ratios))
            mre = float(np.mean(np.abs(true_mean - ratios) / true_mean))
            spread = (
                float(np.max(np.abs(ratios - current_mean)) / abs(current_mean))
                if abs(current_mean) > 1e-30 else float("inf")
            )
            avg_traffic = float(np.mean(list(state["tx_counts"].values())))

        elapsed = time.time() - start_time
        print(
            f"t={elapsed:5.0f}s | Est={current_mean:.4f} | "
            f"MRE={mre*100:.2f}% | Spread={spread:.2e} | "
            f"Mass={current_mass/initial_mass*100:.1f}% | "
            f"Msgs/node={avg_traffic:.0f}"
        )

        if spread < TOLERANCE:
            stability_counter += 1
            if stability_counter >= REQUIRED_STABLE:
                stop_event.set()
                return {
                    "run":         run_idx,
                    "true_mean":   true_mean,
                    "est_mean":    current_mean,
                    "mre_pct":     mre * 100,
                    "acceptable":  mre <= 0.05,
                    "avg_traffic": avg_traffic,
                    "elapsed_s":   elapsed,
                }
        else:
            stability_counter = 0


def main():
    # csv header
    file_exists = SUMMARY_FILE.exists()
    if not file_exists:
        with open(SUMMARY_FILE, "w", newline="") as sf:
            csv.writer(sf).writerow([
                "Timestamp", "Run", "Packet_Loss_Pct",
                "True_Mean", "Est_Mean", "MRE_Percent",
                "Acceptable", "Avg_Traffic", "Elapsed_s"
            ])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_log = OUTPUT_DIR / f"raw_20runs_{ts}.csv"

    print(f"Starting {NUM_RUNS}-run automated experiment")
    print(f"Raw log  : {raw_log}")
    print(f"Summary  : {SUMMARY_FILE}")
    print(f"Ports    : {ESP32_PORTS}\n")

    passed = 0
    failed = 0

    with open(raw_log, "w", newline="") as rf:
        raw_writer = csv.writer(rf)
        raw_writer.writerow([
            "timestamp", "run", "port", "mac",
            "event_type", "value", "weight", "ratio"
        ])

        for run_idx in range(1, NUM_RUNS + 1):
            print(f"\n{'='*60}")
            print(f"RUN {run_idx}/{NUM_RUNS}")
            print(f"{'='*60}")

            reset_boards()

            result = run_single_experiment(run_idx, raw_writer, rf)

            if result is None:
                failed += 1
                print(f"[run {run_idx}] FAILED — skipping to next run")
            else:
                passed += 1
                with open(SUMMARY_FILE, "a", newline="") as sf:
                    csv.writer(sf).writerow([
                        datetime.now().isoformat(),
                        result["run"],
                        PACKET_LOSS_PCT,
                        result["true_mean"],
                        result["est_mean"],
                        result["mre_pct"],
                        result["acceptable"],
                        result["avg_traffic"],
                        result["elapsed_s"],
                    ])

                print(
                    f"\nRUN {run_idx} DONE — "
                    f"MRE={result['mre_pct']:.2f}%  "
                    f"OK={result['acceptable']}  "
                    f"Msgs/node={result['avg_traffic']:.1f}  "
                    f"Time={result['elapsed_s']:.0f}s"
                )

            if run_idx < NUM_RUNS:
                print(f"\n[main] Waiting {INTER_RUN_DELAY}s before next run...")
                time.sleep(INTER_RUN_DELAY)

    print(f"\n{'='*60}")
    print(f"ALL RUNS COMPLETE:  {passed} passed / {failed} failed")
    print(f"Summary: {SUMMARY_FILE}")
    print(f"Raw log: {raw_log}")
    print(f"{'='*60}")

# Entry point
if __name__ == "__main__":
    main()
