#!/usr/bin/env bash
# Demo ACLs: lets demo-user-001 produce/consume demo-topic with consumer group demo-consumer-group.
# Usage: scripts/acls.sh <ha|slim>
set -euo pipefail
DIR="$(dirname "$0")"
V="${1:-}"
"$DIR/kafka-cli.sh" "$V" kafka-acls --add --allow-principal User:demo-user-001 \
  --operation All --topic demo-topic
"$DIR/kafka-cli.sh" "$V" kafka-acls --add --allow-principal User:demo-user-001 \
  --operation All --group demo-consumer-group
"$DIR/kafka-cli.sh" "$V" kafka-acls --add --allow-principal User:demo-user-001 \
  --operation Describe --cluster
