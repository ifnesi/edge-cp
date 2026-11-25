"""Consumes Avro records (schema fetched from Schema Registry) over SASL_SSL."""

import os

from confluent_kafka import Consumer, KafkaException
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import MessageField, SerializationContext
from typing import Any

from common import KAFKA_CONFIG, SR_CONFIG, TOPIC

consumer: Any = Consumer(
    {
        **KAFKA_CONFIG,
        "group.id": os.getenv("GROUP_ID", "demo-consumer-group"),
        "auto.offset.reset": "earliest",
    }
)
avro_deserializer: Any = AvroDeserializer(SchemaRegistryClient(SR_CONFIG))
consumer.subscribe([TOPIC])

print(f"Listening on {TOPIC} via {KAFKA_CONFIG['bootstrap.servers']} (Ctrl+C to stop)")
try:
    while True:
        msg: Any = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())
        value = avro_deserializer(
            msg.value(),
            SerializationContext(
                msg.topic(),
                MessageField.VALUE,
            ),
        )
        print(f"key={msg.key().decode() if msg.key() else None} value={value}")
except KeyboardInterrupt:
    print("Consumer interrupted. Exiting...")
finally:
    consumer.close()
