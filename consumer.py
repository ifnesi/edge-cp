import socket

from confluent_kafka import Consumer, KafkaException
from confluent_kafka.serialization import StringDeserializer

# Consumer instance
consumer = Consumer(
    {
        "bootstrap.servers": "local.kafka.cp-poc:9092",
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": "catalina-001",
        "sasl.password": "catalina-001-secret",
        "ssl.ca.location": "/Users/inesi/Documents/_CFLT/Dev/Docker/edge-cp/sslcerts/cacerts.pem",
        "ssl.endpoint.identification.algorithm": "none",
        "client.id": socket.gethostname(),
        "group.id": "catalina-consumer-group",
        "auto.offset.reset": "earliest",
        # "debug": "all",
    }
)

consumer.subscribe(["catalina-test"])

print("Listening for messages...")
string_deserializer = StringDeserializer("utf_8")

try:
    while True:
        msg = consumer.poll(1.0)  # Timeout of 1 second
        if msg is not None:
            if msg.error():
                raise KafkaException(msg.error())
            else:
                print(f"key: {string_deserializer(msg.key()) if msg.key() else None}")
                print(f"Value: {string_deserializer(msg.value())}\n")
except KeyboardInterrupt:
    print("Consumer interrupted. Exiting...")
finally:
    consumer.close()
