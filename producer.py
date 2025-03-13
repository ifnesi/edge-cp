import socket

from confluent_kafka import Producer


# Producer instance
producer = Producer(
    {
        "bootstrap.servers": "local.kafka.sainsburys:9092",
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": "kafka",
        "sasl.password": "kafka-secret",
        "ssl.ca.location": "/Users/inesi/Documents/_CFLT/Dev/Docker/edge-cp/sslcerts/ca.pem",
        "ssl.endpoint.identification.algorithm": "none",
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
    producer.produce(
        "demotopic",
        key=str(n),
        value=f"Test message {n}",
        callback=acked,
    )
    producer.poll(0)

producer.flush()
