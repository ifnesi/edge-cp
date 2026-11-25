"""Produces Avro records (schema registered in Schema Registry) over SASL_SSL."""

import time
import uuid

from faker import Faker
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import (
    MessageField,
    SerializationContext,
    StringSerializer,
)
from typing import Any

from common import KAFKA_CONFIG, SCHEMA, SR_CONFIG, TOPIC

producer: Any = Producer({**KAFKA_CONFIG, "acks": "all"})
avro_serializer: Any = AvroSerializer(SchemaRegistryClient(SR_CONFIG), SCHEMA)
key_serializer: Any = StringSerializer("utf_8")


def acked(err, msg) -> None:
    if err is not None:
        print(f"Failed to deliver message: {err.str()}")
    else:
        print(
            f"Produced to {msg.topic()} [{msg.partition()}] @ {msg.offset()} key={msg.key().decode()}"
        )


fake: Faker = Faker()
print(f"Producing to {TOPIC} via {KAFKA_CONFIG['bootstrap.servers']} (Ctrl+C to stop)")
try:
    while True:
        value: dict[str, str] = {
            "name": fake.name(),
            "address": fake.address(),
            "ip": fake.ipv4(),
        }
        producer.produce(
            TOPIC,
            key=key_serializer(uuid.uuid4().hex),
            value=avro_serializer(
                value,
                SerializationContext(
                    TOPIC,
                    MessageField.VALUE,
                ),
            ),
            on_delivery=acked,
        )
        producer.poll(0)
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Producer interrupted. Exiting...")
finally:
    print("Flushing producer")
    producer.flush()
