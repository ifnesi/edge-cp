#!/usr/bin/env bash
# Prints the /etc/hosts entries and the external endpoints for one variant.
#  - colima: every hostname maps to the k3s node IP (NodePorts)
#  - aks:    each hostname maps to its Azure LoadBalancer IP
# Usage: scripts/etc_hosts.sh <ha|slim> [colima|aks]
source "$(dirname "$0")/env.sh" "${1:-}" "${2:-}"

host_for_svc() {
  case "$1" in
    kafka-bootstrap-lb|kafka-external) echo "kafka.$DOMAIN" ;;
    kafka-[0-9]*-lb)                   echo "b$(sed -E 's/kafka-([0-9]+)-lb/\1/' <<<"$1").$DOMAIN" ;;
    kafka-kafka-rest-bootstrap-lb)     echo "rest.$DOMAIN" ;;
    schemaregistry-bootstrap-lb)       echo "sr.$DOMAIN" ;;
    controlcenter-bootstrap-lb)        echo "c3.$DOMAIN" ;;
  esac
}

echo -e "\n# Add to /etc/hosts (sudo vi /etc/hosts):"
if [[ "$PLATFORM" == "colima" ]]; then
  IP=$(command kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' | awk '{print $1}')
  echo "$IP kafka.$DOMAIN sr.$DOMAIN c3.$DOMAIN"
else
  kc get svc -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.name} {.status.loadBalancer.ingress[0].ip}{"\n"}{end}' |
  while read -r SVC IP; do
    H=$(host_for_svc "$SVC"); [[ -n "$H" ]] || continue
    echo "${IP:-<pending>} $H"
  done
fi

cat <<OUT

# External endpoints ($NAMESPACE on $PLATFORM):
#   Kafka bootstrap (SASL_SSL) : $BOOTSTRAP
#   Schema Registry (HTTPS)    : $SR_URL
#   Control Center  (HTTPS)    : $C3_URL
OUT
[[ -n "$REST_PORT" ]] && echo "#   Kafka REST v3   (HTTPS)    : https://rest.$DOMAIN:$REST_PORT/kafka/v3/clusters"
echo
