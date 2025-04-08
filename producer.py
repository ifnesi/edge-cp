import json
import uuid
import socket
import time

from faker import Faker
from confluent_kafka import Producer
from confluent_kafka.serialization import StringSerializer, StringDeserializer


# Producer instance
producer = Producer(
    {
        "bootstrap.servers": "local.kafka.sainsburys-poc:9092",
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": "catalina-001",
        "sasl.password": "catalina-001-secret",
        "ssl.ca.location": "/Users/inesi/Documents/_CFLT/Dev/Docker/edge-cp/sslcerts/cacerts.pem",
        "ssl.endpoint.identification.algorithm": "none",
        "client.id": socket.gethostname(),
        # "debug": "all",
    }
)


def acked(err, msg):
    """Delivery report callback"""
    if err is not None:
        print(f"Failed to deliver message: {err.str()}")
    else:
        print(f"Produced to: {msg.topic()} [{msg.partition()}] @ {msg.offset()}")
        print(f" - Key: {string_deserializer(msg.key()) if msg.key() else None}")
        print(f" - Value: {string_deserializer(msg.value())}")


# Produce messages
f = Faker()
string_serializer = StringSerializer("utf_8")
string_deserializer = StringDeserializer("utf_8")
try:
    while True:
        key = uuid.uuid4().hex
        value = {"name": f.name(), "address": f.address(), "ip": f.ipv4()}
        producer.produce(
            "catalina-test",
            key=string_serializer(key),
            value=string_serializer(json.dumps(value)),
            callback=acked,
        )
        producer.poll(0)
        time.sleep(1)
except KeyboardInterrupt:
    print("Producer interrupted. Exiting...")
except Exception as err:
    print(f"ERROR: {err}")
finally:
    print("Flushing producer")
    producer.flush()
