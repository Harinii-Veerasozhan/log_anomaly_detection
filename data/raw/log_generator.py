"""
Synthetic IT System Log Generator
----------------------------------
Continuously writes realistic-looking log lines to a text file, simulating
a real server. Most of the time it writes "normal" activity, but you can
trigger anomalies on demand (great for live demos) or let it inject them
randomly (great for training/testing your detection models).

Usage:
    python log_generator.py                     # normal random mode
    python log_generator.py --demo               # interactive demo mode (press keys to trigger anomalies)

Output:
    Appends lines to logs/system.log in the format:
    2026-08-18 10:32:15 | Server-1 | INFO | CPU=42% | MEM=55% | logins_failed=0 | resp_ms=120 | msg=...
"""

import time
import random
import argparse
import threading
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "system.log"

SERVERS = ["Server-1", "Server-2", "Server-3"]

# Baseline "normal" ranges — your detection model should learn these as normal
NORMAL = {
    "cpu": (20, 45),
    "mem": (30, 60),
    "failed_logins": (0, 2),
    "resp_ms": (80, 200),
    "error_count": (0, 1),
}

# Shared state so anomalies can be triggered live from another thread (demo mode)
active_anomaly = {"type": None, "until": 0}


def inject_anomaly(kind: str, duration_sec: int = 20):
    """Trigger an anomaly for a set duration. Call this from demo mode or randomly."""
    active_anomaly["type"] = kind
    active_anomaly["until"] = time.time() + duration_sec
    print(f"\n>>> ANOMALY INJECTED: {kind} (lasting {duration_sec}s)\n")


def get_current_metrics():
    """Generate one log entry's worth of metrics, applying an anomaly if active."""
    now = time.time()
    anomaly_active = active_anomaly["type"] and now < active_anomaly["until"]
    kind = active_anomaly["type"] if anomaly_active else None

    cpu = random.uniform(*NORMAL["cpu"])
    mem = random.uniform(*NORMAL["mem"])
    failed_logins = random.randint(*NORMAL["failed_logins"])
    resp_ms = random.uniform(*NORMAL["resp_ms"])
    error_count = random.randint(*NORMAL["error_count"])
    msg = "heartbeat OK"

    if kind == "cpu_spike":
        cpu = random.uniform(90, 100)
        msg = "high CPU load detected"
    elif kind == "mem_leak":
        mem = random.uniform(88, 99)
        msg = "high memory usage detected"
    elif kind == "failed_logins":
        failed_logins = random.randint(30, 60)
        msg = "multiple failed login attempts"
    elif kind == "error_burst":
        error_count = random.randint(50, 150)
        msg = "repeated application errors"
    elif kind == "traffic_spike":
        resp_ms = random.uniform(2000, 6000)
        msg = "response time degraded under load"

    if not anomaly_active and cpu > NORMAL["cpu"][1]:
        cpu = random.uniform(*NORMAL["cpu"])  # clamp back to normal safety

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server": random.choice(SERVERS),
        "level": "ERROR" if kind else "INFO",
        "cpu": round(cpu, 1),
        "mem": round(mem, 1),
        "failed_logins": failed_logins,
        "resp_ms": round(resp_ms, 1),
        "error_count": error_count,
        "msg": msg,
    }


def format_line(entry: dict) -> str:
    return (
        f"{entry['timestamp']} | {entry['server']} | {entry['level']} | "
        f"CPU={entry['cpu']}% | MEM={entry['mem']}% | "
        f"logins_failed={entry['failed_logins']} | resp_ms={entry['resp_ms']} | "
        f"errors={entry['error_count']} | msg={entry['msg']}"
    )


def write_loop(interval_sec: float, random_anomalies: bool):
    print(f"Writing logs to: {LOG_FILE}")
    print("Press Ctrl+C to stop.\n")
    tick = 0
    with open(LOG_FILE, "a") as f:
        while True:
            entry = get_current_metrics()
            line = format_line(entry)
            f.write(line + "\n")
            f.flush()
            print(line)

            # Occasionally trigger a random anomaly if enabled (good for model training data)
            if random_anomalies and tick % 40 == 0 and random.random() < 0.5:
                inject_anomaly(random.choice(
                    ["cpu_spike", "mem_leak", "failed_logins", "error_burst", "traffic_spike"]
                ), duration_sec=random.randint(10, 25))

            tick += 1
            time.sleep(interval_sec)


def demo_control_loop():
    """Lets you type a command to trigger an anomaly live during a demo."""
    options = {
        "1": ("cpu_spike", "CPU spike"),
        "2": ("mem_leak", "Memory leak"),
        "3": ("failed_logins", "Failed login burst (brute force)"),
        "4": ("error_burst", "Application error burst"),
        "5": ("traffic_spike", "Traffic/latency spike"),
    }
    while True:
        print("\nTrigger an anomaly for the demo:")
        for k, (_, label) in options.items():
            print(f"  {k}. {label}")
        print("  q. Quit")
        choice = input("> ").strip()
        if choice == "q":
            break
        if choice in options:
            inject_anomaly(options[choice][0], duration_sec=20)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Interactive demo mode: trigger anomalies on command")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between log lines")
    parser.add_argument("--no-random", action="store_true", help="Disable automatic random anomalies")
    args = parser.parse_args()

    writer_thread = threading.Thread(
        target=write_loop,
        args=(args.interval, not args.demo and not args.no_random),
        daemon=True,
    )
    writer_thread.start()

    if args.demo:
        demo_control_loop()
    else:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopped.")