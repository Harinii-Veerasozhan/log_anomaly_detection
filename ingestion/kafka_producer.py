"""
Kafka Log Producer
---------------------
Generates synthetic logs and publishes each one as a message to a Kafka topic.

Install first: pip install confluent-kafka

Run:
    python ingestion/kafka_producer.py
    python ingestion/kafka_producer.py --demo
"""

import time
import random
import json
import argparse
import threading
import os
from datetime import datetime
from confluent_kafka import Producer

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = "system-logs"

producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})

SERVERS = ["Server-1", "Server-2", "Server-3"]
NORMAL = {
    "cpu": (20, 45), "mem": (30, 60), "failed_logins": (0, 2),
    "resp_ms": (80, 200), "error_count": (0, 1),
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
        cpu = random.uniform(90, 100); msg = "high CPU load detected"
    elif kind == "mem_leak":
        mem = random.uniform(88, 99); msg = "high memory usage detected"
    elif kind == "failed_logins":
        failed_logins = random.randint(30, 60); msg = "multiple failed login attempts"
    elif kind == "error_burst":
        error_count = random.randint(50, 150); msg = "repeated application errors"
    elif kind == "traffic_spike":
        resp_ms = random.uniform(2000, 6000); msg = "response time degraded under load"

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server": random.choice(SERVERS),
        "level": "ERROR" if kind else "INFO",
        "cpu": round(cpu, 1), "mem": round(mem, 1),
        "failed_logins": failed_logins, "resp_ms": round(resp_ms, 1),
        "error_count": error_count, "msg": msg,
    }


def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")


def write_loop(interval_sec: float, random_anomalies: bool):
    print(f"Publishing to Kafka topic: {TOPIC}")
    tick = 0
    while True:
        entry = get_current_metrics()
        producer.produce(TOPIC, json.dumps(entry).encode("utf-8"), callback=delivery_report)
        producer.poll(0)
        print(entry)

        if random_anomalies and tick % 40 == 0 and random.random() < 0.5:
            inject_anomaly(random.choice(
                ["cpu_spike", "mem_leak", "failed_logins", "error_burst", "traffic_spike"]
            ), duration_sec=random.randint(10, 25))

        tick += 1
        time.sleep(interval_sec)


def demo_control_loop():
    options = {
        "1": ("cpu_spike", "CPU spike"), "2": ("mem_leak", "Memory leak"),
        "3": ("failed_logins", "Failed login burst"), "4": ("error_burst", "Error burst"),
        "5": ("traffic_spike", "Traffic spike"),
    }
    while True:
        print("\nTrigger an anomaly:")
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
    args = parser.parse_args()

    t = threading.Thread(target=write_loop, args=(args.interval, not args.demo), daemon=True)
    t.start()

    if args.demo:
        demo_control_loop()
    else:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            producer.flush()
            print("\nStopped.")