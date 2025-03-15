import socket

from confluent_kafka import Consumer, KafkaException

# Consumer instance
consumer = Consumer(
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
        "group.id": "catalina-consumer-group",
        "auto.offset.reset": "earliest",
    }
)

consumer.subscribe(["catalina-test"])

print("Listening for messages...")

try:
    while True:
        msg = consumer.poll(1.0)  # Timeout of 1 second
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        print(
            f"Received message: {msg.value().decode('utf-8')} (key: {msg.key().decode('utf-8') if msg.key() else None})"
        )
except KeyboardInterrupt:
    print("Consumer interrupted. Exiting...")
finally:
    consumer.close()
