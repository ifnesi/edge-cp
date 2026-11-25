#!/usr/bin/env bash
# End-to-end deploy of one variant: CFK operator, certs, secrets, CP components.
# Usage: scripts/deploy.sh <ha|slim> [colima|aks]
set -euo pipefail
source "$(dirname "$0")/env.sh" "${1:-}" "${2:-}"
cd "$ROOT_DIR"

echo ">> Deploying $VARIANT on $PLATFORM (namespace $NAMESPACE, manifests $K8S_DIR)"
command kubectl create namespace "$NAMESPACE" 2>/dev/null || true

echo ">> Installing CFK (chart $CFK_CHART_VERSION)"
helm repo add confluentinc https://packages.confluent.io/helm >/dev/null 2>&1 || true
helm repo update confluentinc >/dev/null
# Add --set licenseKey=<key> to apply a global CP licence (and set spec.license.globalLicense: true in the CRs)
helm upgrade --install confluent-operator confluentinc/confluent-for-kubernetes \
  --version "$CFK_CHART_VERSION" --namespace "$NAMESPACE" --set kRaftEnabled=true --wait

"$ROOT_DIR/scripts/certs.sh" "$VARIANT" "$PLATFORM"
"$ROOT_DIR/scripts/secrets.sh" "$VARIANT" "$PLATFORM"

echo ">> Applying $K8S_DIR"
command kubectl apply -k "$K8S_DIR"

echo ">> Waiting for Confluent Platform (this takes a few minutes)"
for cr in kraftcontroller kafka schemaregistry controlcenter; do
  kc get "$cr" >/dev/null 2>&1 || continue
  for name in $(kc get "$cr" -o name); do
    until [[ "$(kc get "$name" -o jsonpath='{.status.phase}')" == "RUNNING" ]]; do sleep 10; done
    echo "   $name RUNNING"
  done
done
kc get pods
"$ROOT_DIR/scripts/etc_hosts.sh" "$VARIANT" "$PLATFORM"
