#!/bin/bash

# Get all Kafka-related services with LoadBalancer type
SERVICES=$(kubectl get svc -n $NAMESPACE --no-headers | grep kafka | grep LoadBalancer)

# Print header
echo -e "\n# Entries for /etc/hosts:"

# Process each service
while IFS= read -r line; do
  SERVICE_NAME=$(echo "$line" | awk '{print $1}')
  EXTERNAL_IP=$(echo "$line" | awk '{print $4}')
  
  # Skip services without an external IP
  if [[ "$EXTERNAL_IP" == "<none>" || -z "$EXTERNAL_IP" ]]; then
    continue
  fi

  # Determine the hostname
  if [[ "$SERVICE_NAME" == "kafka-bootstrap-lb" ]]; then
    HOSTNAME="$DOMAIN"
  elif [[ "$SERVICE_NAME" == "kafka-rest-lb" ]]; then
    HOSTNAME="kafka.$DOMAIN"
  else
    BROKER_ID=$(echo "$SERVICE_NAME" | sed -E 's/kafka-([0-9]+)-lb/\1/')
    HOSTNAME="b$BROKER_ID.$DOMAIN"
  fi

  # Print entry
  echo "$EXTERNAL_IP $HOSTNAME"
done <<< "$SERVICES"
echo ""