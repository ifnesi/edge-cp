"""Shared client settings. Override with env vars, e.g.:
VARIANT=ha python3 scripts/python/producer.py
"""

import os
import socket
from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parents[2]

VARIANT: str = os.getenv("VARIANT", "slim")  # slim | ha
DOMAIN: str = os.getenv("DOMAIN", f"cp-edge-{VARIANT}.test")
KAFKA_PORT, SR_PORT = {
    "ha": (9092, 8081),
    "slim": (31000, 31081),
}[VARIANT]

TOPIC = os.getenv("TOPIC", "demo-topic")
CA_FILE = os.getenv("CA_FILE", str(ROOT_DIR / "certs" / "ca.pem"))

KAFKA_CONFIG = {
    "bootstrap.servers": os.getenv("BOOTSTRAP", f"kafka.{DOMAIN}:{KAFKA_PORT}"),
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": os.getenv("KAFKA_USER", "demo-user-001"),
    "sasl.password": os.getenv("KAFKA_PASSWORD", "demo-user-001-secret"),
    "ssl.ca.location": CA_FILE,  # hostname verification stays on: the cert has the right SANs
    "client.id": socket.gethostname(),
}

SR_CONFIG = {
    "url": os.getenv("SR_URL", f"https://sr.{DOMAIN}:{SR_PORT}"),
    "basic.auth.user.info": os.getenv(
        "SR_API_KEY", "demo-user-001:demo-user-001-sr-secret"
    ),
    "ssl.ca.location": CA_FILE,
}

SCHEMA = """
{
  "type": "record",
  "name": "Customer",
  "namespace": "edge.cp",
  "fields": [
    {"name": "name",    "type": "string"},
    {"name": "address", "type": "string"},
    {"name": "ip",      "type": "string"}
  ]
}
"""
