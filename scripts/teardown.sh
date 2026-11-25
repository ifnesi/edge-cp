#!/usr/bin/env bash
# Removes one variant entirely (CP components, PVCs, operator, namespace).
# Usage: scripts/teardown.sh <ha|slim> [colima|aks]
set -euo pipefail
source "$(dirname "$0")/env.sh" "${1:-}" "${2:-}"
kc delete kafkatopic --all --ignore-not-found
command kubectl delete -k "$K8S_DIR" --ignore-not-found
helm uninstall confluent-operator -n "$NAMESPACE" 2>/dev/null || true
command kubectl delete namespace "$NAMESPACE" --ignore-not-found
rm -rf "$CERTS_DIR/$NAMESPACE"
