#!/usr/bin/env bash
# Runs any Kafka CLI tool inside the cluster as the `kafka` super user, over the internal
# SASL_SSL listener (no local Java needed). The client config is written to /tmp/admin.properties.
#
# Plain tools run in the first broker pod (kafka-0). The Avro tools (kafka-avro-console-producer /
# kafka-avro-console-consumer) only ship in the Schema Registry image, so they run in schemaregistry-0
# and get the Schema Registry URL (HTTPS), truststore and API key (config/credentials/sr-client.txt)
# added automatically.
#
# Usage: scripts/kafka-cli.sh <ha|slim> <tool> [args...]
#   e.g. scripts/kafka-cli.sh slim kafka-topics --list
#        scripts/kafka-cli.sh slim kafka-acls --list
#        scripts/kafka-cli.sh slim kafka-console-consumer --topic perf-topic --from-beginning --max-messages 5
#        scripts/kafka-cli.sh slim kafka-avro-console-consumer --topic demo-topic --from-beginning
#        scripts/kafka-cli.sh slim kafka-avro-console-producer --topic demo-topic \
#          --reader-property value.schema.id=<id>      # or value.schema='<Avro schema JSON>'
set -euo pipefail
source "$(dirname "$0")/env.sh" "${1:-}" "${PLATFORM:-}"
shift
[[ $# -ge 1 ]] || { echo "Usage: $(basename "$0") <ha|slim> <tool> [args...]" >&2; exit 1; }

POD=kafka-0
CONTAINER=kafka
BOOT="kafka.$NAMESPACE.svc.cluster.local:9071"
TOOL=$1; shift
SR_ARGS=()

# --command-config / --producer.config / --consumer.config depending on the tool
case "$TOOL" in
  kafka-console-producer|kafka-verifiable-producer|kafka-producer-perf-test|kafka-avro-console-producer)
    CFG=(--producer.config /tmp/admin.properties) ;;
  kafka-console-consumer|kafka-verifiable-consumer|kafka-consumer-perf-test|kafka-avro-console-consumer)
    CFG=(--consumer.config /tmp/admin.properties) ;;
  *) CFG=(--command-config /tmp/admin.properties) ;;
esac
case "$TOOL" in
  kafka-producer-perf-test) BOOT_ARGS=() ;;   # takes bootstrap.servers from the config file
  *) BOOT_ARGS=(--bootstrap-server "$BOOT") ;;
esac

# Avro tools: run in the Schema Registry pod, with the SR client settings as formatter/reader properties
case "$TOOL" in
  kafka-avro-console-producer|kafka-avro-console-consumer)
    POD=schemaregistry-0
    CONTAINER=schemaregistry
    [[ $TOOL == *producer ]] && FLAG=--reader-property || FLAG=--formatter-property
    SR_USER=$(sed -n 's/^username=//p' "$CREDS_DIR/sr-client.txt")
    SR_PASS=$(sed -n 's/^password=//p' "$CREDS_DIR/sr-client.txt")
    for P in \
      "schema.registry.url=https://schemaregistry.$NAMESPACE.svc.cluster.local:8081" \
      "basic.auth.credentials.source=USER_INFO" \
      "basic.auth.user.info=$SR_USER:$SR_PASS" \
      "schema.registry.ssl.truststore.location=/mnt/sslcerts/truststore.p12" \
      "schema.registry.ssl.truststore.type=PKCS12" \
      "schema.registry.ssl.truststore.password=__JKS_PASSWORD__"; do
      SR_ARGS+=("$FLAG" "$P")
    done ;;
esac

kc exec -i "$POD" -c "$CONTAINER" -- bash -c '
  export LOG_DIR=/tmp   # Avro tools (SR image) otherwise log to a read-only dir
  P=$(cut -d= -f2 /mnt/sslcerts/jksPassword.txt)
  cat > /tmp/admin.properties <<PROPS
bootstrap.servers='"$BOOT"'
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username="kafka" password="kafka-secret";
ssl.truststore.location=/mnt/sslcerts/truststore.p12
ssl.truststore.type=PKCS12
ssl.truststore.password=$P
PROPS
  ARGS=(); for A in "$@"; do ARGS+=("${A//__JKS_PASSWORD__/$P}"); done
  exec "${ARGS[@]}"' _ "$TOOL" ${BOOT_ARGS[@]+"${BOOT_ARGS[@]}"} "${CFG[@]}" ${SR_ARGS[@]+"${SR_ARGS[@]}"} "$@"
