#!/usr/bin/env bash
# Creates/updates the credential secrets from config/credentials/.
# Kafka PLAIN users (kafka-users.json) are hot-reloaded by the brokers, so re-running this after
# adding a user is enough (no restart).
# Usage: scripts/secrets.sh <ha|slim> [colima|aks]
set -euo pipefail
source "$(dirname "$0")/env.sh" "${1:-}" "${2:-}"
command kubectl create namespace "$NAMESPACE" 2>/dev/null || true

apply_secret() { local name=$1; shift; kc create secret generic "$name" "$@" --dry-run=client -o yaml | kc apply -f -; }

# Kafka SASL/PLAIN
#  plain-users.json          server-side user store (all listeners)
#  plain.txt                 client creds for SR / C3 -> Kafka
#  plain-interbroker.txt     broker <-> broker and broker <-> KRaft creds
#  ...-internal-plain-metrics.txt  CFK telemetry/metrics client creds
apply_secret kafka-credential \
  --from-file=plain-users.json="$CREDS_DIR/kafka-users.json" \
  --from-file=plain.txt="$CREDS_DIR/kafka-client.txt" \
  --from-file=plain-interbroker.txt="$CREDS_DIR/kafka-client.txt" \
  --from-file=kafka-server-listener-internal-plain-metrics.txt="$CREDS_DIR/kafka-client.txt"
# Embedded Kafka REST (Admin API v3): server-side users and client creds (KafkaRestClass)
apply_secret rest-users  --from-file=basic.txt="$CREDS_DIR/rest-users.txt"
apply_secret rest-client --from-file=basic.txt="$CREDS_DIR/rest-client.txt"
# Schema Registry: server-side "API keys" (user: secret,role) and client creds (C3 -> SR)
apply_secret sr-users  --from-file=basic.txt="$CREDS_DIR/sr-users.txt"
apply_secret sr-client --from-file=basic.txt="$CREDS_DIR/sr-client.txt"
# Control Center UI login
apply_secret c3-users --from-file=basic.txt="$CREDS_DIR/c3-users.txt"
