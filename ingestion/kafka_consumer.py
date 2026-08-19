"""
Kafka Log Consumer
---------------------
Subscribes to the system-logs topic and processes each message as it arrives.

Install first: pip install confluent-kafka

Run standalone to test:
    python ingestion/kafka_consumer.py
"""

import json
from confluent_kafka import Consumer

KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC = "system-logs"
GROUP_ID = "log-anomaly-detector"


def get_consumer():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "latest",
    })
    consumer.subscribe([TOPIC])
    return consumer


def watch(callback):
    """Consumes messages forever, calling callback(parsed_dict) for each one."""
    consumer = get_consumer()
    print(f"Consuming from Kafka topic: {TOPIC}")
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
            entry = json.loads(msg.value().decode("utf-8"))
            callback(entry)
    finally:
        consumer.close()


if __name__ == "__main__":
    def print_entry(entry):
        print(f"[{entry['timestamp']}] {entry['server']} CPU={entry['cpu']}% -> {entry['msg']}")

    watch(print_entry)