#!/usr/bin/env bash
# Shared settings for all scripts.
# Usage (from other scripts): source scripts/env.sh <ha|slim> [colima|aks]
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VARIANT="${1:-${VARIANT:-}}"
PLATFORM="${2:-${PLATFORM:-}}"
case "$VARIANT" in
  ha)
    PLATFORM="${PLATFORM:-aks}"
    [[ "$PLATFORM" == "aks" ]] || { echo "The HA variant needs a multi-node cluster (aks)" >&2; exit 1; }
    K8S_DIR="$ROOT_DIR/k8s/ha"
    KAFKA_PORT=9092; SR_PORT=8081; C3_PORT=9021; REST_PORT=8090
    ;;
  slim)
    PLATFORM="${PLATFORM:-colima}"
    [[ "$PLATFORM" =~ ^(colima|aks)$ ]] || { echo "PLATFORM must be colima or aks" >&2; exit 1; }
    K8S_DIR="$ROOT_DIR/k8s/slim/$PLATFORM"
    KAFKA_PORT=31000; SR_PORT=31081; C3_PORT=31021; REST_PORT=""
    ;;
  *) echo "Usage: $(basename "$0") <ha|slim> [colima|aks]" >&2; exit 1 ;;
esac
export VARIANT PLATFORM K8S_DIR KAFKA_PORT SR_PORT C3_PORT REST_PORT
export NAMESPACE="cp-edge-$VARIANT"
export DOMAIN="cp-edge-$VARIANT.test"        # external hostnames are <prefix>.$DOMAIN (scripts/etc_hosts.sh)
export BOOTSTRAP="kafka.$DOMAIN:$KAFKA_PORT"
export SR_URL="https://sr.$DOMAIN:$SR_PORT"
export C3_URL="https://c3.$DOMAIN:$C3_PORT"
export CFK_CHART_VERSION="${CFK_CHART_VERSION:-0.2038.24}"   # CFK 3.4.1

export CERTS_DIR="$ROOT_DIR/certs"
export CREDS_DIR="$ROOT_DIR/config/credentials"
export STORE_PASSWORD="${STORE_PASSWORD:-changeit}"  # client truststore (config/client/client.properties)

kc() { command kubectl -n "$NAMESPACE" "$@"; }
