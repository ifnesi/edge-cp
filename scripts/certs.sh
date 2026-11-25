#!/usr/bin/env bash
# Generates (once) a self-signed CA shared by both variants, a server certificate for the
# given variant, a PKCS12 truststore for Java clients, and the `tls-cp` K8s secret.
# Usage: scripts/certs.sh <ha|slim> [colima|aks]
set -euo pipefail
source "$(dirname "$0")/env.sh" "${1:-}" "${2:-}"

mkdir -p "$CERTS_DIR/$NAMESPACE"
cd "$CERTS_DIR"

if [[ ! -f ca.pem ]]; then
  echo ">> Generating self-signed CA"
  openssl req -x509 -new -nodes -newkey rsa:2048 -sha256 -days 3650 \
    -keyout ca-key.pem -out ca.pem -subj "/C=GB/O=Edge-CP PoC/CN=Edge-CP PoC CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -addext "subjectKeyIdentifier=hash" 2>/dev/null
fi

if [[ ! -f truststore.p12 ]]; then
  echo ">> Generating client truststore (truststore.p12)"
  # -jdktrust marks the CA as a trusted entry for Java, so no keytool/JDK is needed
  openssl pkcs12 -export -nokeys -in ca.pem -name cp-ca -jdktrust anyExtendedKeyUsage \
    -out truststore.p12 -passout pass:"$STORE_PASSWORD"
fi

echo ">> Generating server certificate for $NAMESPACE ($DOMAIN)"
cd "$NAMESPACE"
envsubst '${NAMESPACE} ${DOMAIN}' < "$ROOT_DIR/config/tls/server.cnf" > server.cnf
openssl req -new -nodes -newkey rsa:2048 -keyout server-key.pem -out server.csr -config server.cnf 2>/dev/null
openssl x509 -req -in server.csr -CA ../ca.pem -CAkey ../ca-key.pem -CAcreateserial -sha256 -days 825 \
  -out server.pem -extensions v3_sign -extfile server.cnf 2>/dev/null
cat server.pem ../ca.pem > fullchain.pem
rm -f server.csr

echo ">> Creating secret tls-cp in $NAMESPACE"
command kubectl create namespace "$NAMESPACE" 2>/dev/null || true
kc create secret generic tls-cp \
  --from-file=fullchain.pem=fullchain.pem \
  --from-file=privkey.pem=server-key.pem \
  --from-file=cacerts.pem=../ca.pem \
  --dry-run=client -o yaml | kc apply -f -
