#!/usr/bin/env bash
# Creates demo-topic (Python / Avro clients) and perf-topic (perf tests, plain console tools) with the Kafka CLI (inside the broker pod).
# (The HA variant also creates them declaratively via k8s/ha/topics.yaml - KafkaTopic CRs.)
# Usage: scripts/topics.sh <ha|slim>
set -euo pipefail
DIR="$(dirname "$0")"
V="${1:-}"
case "$V" in ha) RF=3; MISR=2 ;; slim) RF=1; MISR=1 ;; *) echo "Usage: $(basename "$0") <ha|slim>" >&2; exit 1 ;; esac
for T in demo-topic perf-topic; do
  "$DIR/kafka-cli.sh" "$V" kafka-topics --create --if-not-exists --topic "$T" \
    --partitions 3 --replication-factor "$RF" --config min.insync.replicas="$MISR" --config retention.ms=604800000
done
"$DIR/kafka-cli.sh" "$V" kafka-topics --list
