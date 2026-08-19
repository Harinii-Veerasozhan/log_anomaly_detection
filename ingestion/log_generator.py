"""
Synthetic IT System Log Generator
----------------------------------
Writes realistic log lines continuously to data/synthetic/system.log.
Most lines are "normal" activity; anomalies are injected either randomly
(for training data) or on-demand (for live demos).

Run:
    python ingestion/log_generator.py                # normal random mode
    python ingestion/log_generator.py --demo          # interactive demo mode
"""

import time
import random
import argparse
import threading
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "system.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

SERVERS = ["Server-1", "Server-2", "Server-3"]

NORMAL = {
    "cpu": (20, 45),
    "mem": (30, 60),
    "failed_logins": (0, 2),
    "resp_ms": (80, 200),
    "error_count": (0, 1),
}

active_anomaly = {"type": None, "until": 0}


def inject_anomaly(kind: str, duration_sec: int = 20):
    active_anomaly["type"] = kind
    active_anomaly["until"] = time.time() + duration_sec
    print(f"\n>>> ANOMALY INJECTED: {kind} (lasting {duration_sec}s)\n")


def get_current_metrics():
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


def format_line(e: dict) -> str:
    return (
        f"{e['timestamp']} | {e['server']} | {e['level']} | "
        f"CPU={e['cpu']}% | MEM={e['mem']}% | "
        f"logins_failed={e['failed_logins']} | resp_ms={e['resp_ms']} | "
        f"errors={e['error_count']} | msg={e['msg']}"
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

            if random_anomalies and tick % 40 == 0 and random.random() < 0.5:
                inject_anomaly(random.choice(
                    ["cpu_spike", "mem_leak", "failed_logins", "error_burst", "traffic_spike"]
                ), duration_sec=random.randint(10, 25))

            tick += 1
            time.sleep(interval_sec)


def demo_control_loop():
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
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--no-random", action="store_true")
    args = parser.parse_args()

    t = threading.Thread(
        target=write_loop,
        args=(args.interval, not args.demo and not args.no_random),
        daemon=True,
    )
    t.start()

    if args.demo:
        demo_control_loop()
    else:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopped.")