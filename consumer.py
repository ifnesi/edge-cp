import socket

from confluent_kafka import Consumer, KafkaException
from confluent_kafka.serialization import StringDeserializer

# Consumer instance
consumer = Consumer(
    {
        "bootstrap.servers": "local.kafka.sainsburys-poc:9092",
        # "security.protocol": "SASL_SSL",
        "security.protocol": "SASL_PLAINTEXT",
        "sasl.mechanism": "PLAIN",
        "sasl.username": "catalina-001",
        "sasl.password": "catalina-001-secret",
        # "ssl.ca.location": "/Users/inesi/Documents/_CFLT/Dev/Docker/edge-cp/sslcerts/ca.pem",
        # "ssl.endpoint.identification.algorithm": "none",
        "client.id": socket.gethostname(),
        "group.id": "catalina-consumer-group",
        "auto.offset.reset": "earliest",
    }
)

consumer.subscribe(["catalina-test"])

print("Listening for messages...")
string_deserializer = StringDeserializer("utf_8")

try:
    while True:
        msg = consumer.poll(1.0)  # Timeout of 1 second
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        print(f"key: {string_deserializer(msg.key()) if msg.key() else None}")
        print(f"key: {string_deserializer(msg.value())}\n")
except KeyboardInterrupt:
    print("Consumer interrupted. Exiting...")
finally:
    consumer.close()
