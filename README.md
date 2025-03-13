# Edge Confluent Platform

## Requirements and Assumptions
- No REST Proxy (producers/consumers to use the Kafka protocol)
- No C3, ksqlDB, and Schema Registry
- Only KRaft + Confluent Server v7.9.0 (or latest) in combined mode
  - 8 vCPU
  - 16 GB RAM
  - 5 TB disk (persistent storage)
  - One single cluster, no DR
- Single namespace containing the CfK Operator and the CP pod
- Separate namespace for monitoring (and potentially other agents Sainsbury’s may want to deploy)
- Single node Kraft+Confluent Server (combined mode)
  - CFK does not currently provide first class support for KRaft combined mode, so it will be required to use configOverrides
  - Start from the Kraftcontroller CRD as the Kafka CRD requires a 3 node Kraft cluster under CfK
- Self-signed TLS (auto-generated certs)
  - SASL_PLAINTEXT inside the pod (for CONTROLLER and REPLICATION listeners), otherwise need to specify FQDNs for host names (or add localhost to SANs...)
  - No SSL certificate rotation
- File-based user creds store (SASL_SSL with basic creds for external AuthN)
- Kafka ACLs
- No RBACs
- JMX exporter for Prometheus
- Persistent storage (depends on a suitable Storage class)
- No need for the metric reporter

## Deploying the Edge-CP Platform

This deployment utilises [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) to apply the necessary CRD/YAML files for deploying Confluent Platform on Kubernetes. The target environment is **Azure Kubernetes Service (AKS)**. Before proceeding, ensure that kubectl is correctly configured to interact with your AKS cluster. This includes setting up kubectl with the appropriate Azure credentials and context.

1. Create Namespace

```bash
NAMESPACE="sainsburys"
kubectl create namespace $NAMESPACE
kubectl config set-context --current --namespace=$NAMESPACE
```

2. Install Confluent Operator

```bash
helm upgrade --install confluent-operator confluentinc/confluent-for-kubernetes --namespace $NAMESPACE --set kRaftEnabled=true
```

3. Create SSL Self-Signed Certificate

```bash
TUTORIAL_HOME=./sslcerts/
mkdir $TUTORIAL_HOME

openssl genrsa -out $TUTORIAL_HOME/ca-key.pem 2048

openssl req -new -key $TUTORIAL_HOME/ca-key.pem -x509 \
      -days 1000 \
      -out $TUTORIAL_HOME/ca.pem \
      -subj "/C=US/ST=CA/L=MountainView/O=Confluent/OU=Operator/CN=TestCA"

kubectl delete secret ca-pair-sslcerts -n $NAMESPACE
kubectl create secret tls ca-pair-sslcerts \
   --cert=$TUTORIAL_HOME/ca.pem \
   --key=$TUTORIAL_HOME/ca-key.pem

keytool -list -keystore $TUTORIAL_HOME/truststore.jks -storepass mystorepassword

keytool -delete -alias $NAMESPACE -keystore $TUTORIAL_HOME/truststore.jks -storepass mystorepassword
keytool -importcert -alias $NAMESPACE -file $TUTORIAL_HOME/ca.pem -keystore $TUTORIAL_HOME/truststore.jks -storepass mystorepassword -noprompt

keytool -list -keystore $TUTORIAL_HOME/truststore.jks -storepass mystorepassword
```

4. Endpoint

The bootstrap endpoint used in this deployment is a placeholder and will not resolve automatically. To ensure proper connectivity, you must manually register it in your `/etc/hosts` file. This involves mapping the bootstrap hostname to the appropriate IP address of your AKS cluster. Without this step, clients and components may fail to communicate with the Confluent Platform.

```bash
bootstrap=local.kafka.sainsburys:9092
```

5. Apply CRDs

 5.1 Credentials

The authentication credentials for Confluent Platform are managed via Kubernetes Secrets, as defined in the `secrets.yaml` file. If any changes are required—such as updating passwords, adding new users, or modifying existing credentials—the YAML file must be updated accordingly and reapplied using `kubectl apply -f`. Once the updated Secret is applied, the authentication configuration will be refreshed automatically, as per the `refresh_ms="3000"` setting in the listener configuration. This ensures that the system picks up changes within 3 seconds without requiring a manual restart.

```bash
kubectl apply -f secrets.yaml -n $NAMESPACE
```

 5.2 Confluent Platform

```bash
kubectl apply -f confluent_platform.yaml --namespace $NAMESPACE
```

After that wait for the kafka-0 pod to be running and without errors.

```bash
kubectl get pods -n $NAMESPACE
```

 5.3 Topics

This CRD can be used as a template for topics creation.

```bash
kubectl apply -f topics.yaml -n $NAMESPACE
```

List topics:
```bash
kafka-topics --list \
  --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties
```

Execute Performance Tests
```bash
kafka-producer-perf-test \
   --topic demotopic \
   --num-records 20000 \
   --record-size 10000 \
   --throughput -1 \
   --producer.config ./sslcli.properties \
   --producer-props bootstrap.servers=local.kafka.sainsburys:9092 batch.size=100
```

 5.4 ACLs

List ACLs

```bash
kafka-acls --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
  --list
```

Add ACLs
```bash
kafka-acls --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
  --add \
  --allow-principal "User:catalina-001" \
  --operation All \
  --topic 'catalina*' \
  --group '*'
```

## Tearing it down
```bash
NAMESPACE="sainsburys"
kubectl config set-context --current --namespace=$NAMESPACE
kubectl delete -f topics.yaml -n $NAMESPACE
kubectl delete -f confluent_platform.yaml --namespace $NAMESPACE
kubectl delete -f secrets.yaml -n $NAMESPACE
helm uninstall confluent-operator
```