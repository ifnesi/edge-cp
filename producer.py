import socket
import uuid

from confluent_kafka import Producer


# Producer instance
producer = Producer(
    {
        "bootstrap.servers": "local.kafka.sainsburys-poc:9092",
        #"security.protocol": "SASL_SSL",
        "security.protocol": "SASL_PLAINTEXT",
        "sasl.mechanism": "PLAIN",
        "sasl.username": "catalina-001",
        "sasl.password": "catalina-001-secret",
        #"ssl.ca.location": "/Users/inesi/Documents/_CFLT/Dev/Docker/edge-cp/sslcerts/ca.pem",
        #"ssl.endpoint.identification.algorithm": "none",
        "client.id": socket.gethostname(),
    }
)


def acked(err, msg):
    """Delivery report callback"""
    if err is not None:
        print(f"Failed to deliver message: {err.str()}")
    else:
        print(f"Produced to: {msg.topic()} [{msg.partition()}] @ {msg.offset()}")


# Produce messages
for n in range(10):
    key = uuid.uuid4().hex
    producer.produce(
        "catalina-test",
        key=key,
        value=f"Test message: {key}",
        callback=acked,
    )
    producer.poll(0)

producer.flush()
