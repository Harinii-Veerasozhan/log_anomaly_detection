"""Kafka consumer for authentication events."""

import json
import os

from confluent_kafka import Consumer

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = "auth-logs"
GROUP_ID = "auth-log-anomaly-detector"


def get_consumer():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "latest",
    })
    consumer.subscribe([TOPIC])
    return consumer


def watch(callback):
    consumer = get_consumer()
    print(f"Consuming from Kafka topic: {TOPIC}")
    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                print(f"Consumer error: {message.error()}")
                continue
            callback(json.loads(message.value().decode("utf-8")))
    finally:
        consumer.close()