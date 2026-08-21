"""Synthetic authentication log producer for the ``auth-logs`` topic."""

import argparse
import json
import os
import random
import time
from datetime import datetime

from confluent_kafka import Producer

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = "auth-logs"
USERS = ["alice", "bob", "carol", "dave"]
IPS = ["10.0.0.10", "10.0.0.11", "10.0.0.12"]
producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})


def get_auth_event(anomalous: bool = False):
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server": random.choice(["Auth-1", "Auth-2"]),
        "username": random.choice(USERS),
        "source_ip": random.choice(IPS if not anomalous else IPS + [f"10.0.0.{random.randint(20, 99)}"]),
        "success": not anomalous or random.random() > 0.85,
    }


def write_loop(interval_sec: float = 1.0):
    tick = 0
    while True:
        event = get_auth_event(anomalous=tick % 40 >= 30)
        producer.produce(TOPIC, json.dumps(event).encode("utf-8"))
        producer.poll(0)
        print(event)
        tick += 1
        time.sleep(interval_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    try:
        write_loop(args.interval)
    except KeyboardInterrupt:
        producer.flush()
        print("\nStopped.")