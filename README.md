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

### 1. Create Env Vars and Namespace

```bash
bootstrap=local.kafka.sainsburys:9092
NAMESPACE="sainsburys"
kubectl create namespace $NAMESPACE
kubectl config set-context --current --namespace=$NAMESPACE
```

### 2. Install Confluent Operator

```bash
helm upgrade --install confluent-operator confluentinc/confluent-for-kubernetes \
  --namespace $NAMESPACE \
  --set kRaftEnabled=true #--set licenseKey=<CFK license key>
```

### 3. Create SSL Self-Signed Certificate

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

### 4. Apply CRDs

#### 4.1 Credentials

The authentication credentials for Confluent Platform are managed via Kubernetes Secrets, as defined in the `secrets.yaml` file. If any changes are required—such as updating passwords, adding new users, or modifying existing credentials—the YAML file must be updated accordingly and reapplied using `kubectl apply -f`. Once the updated Secret is applied, the authentication configuration will be refreshed automatically, as per the `refresh_ms="3000"` setting in the listener configuration. This ensures that the system picks up changes within 3 seconds without requiring a manual restart.

```bash
kubectl apply -f secrets.yaml -n $NAMESPACE
```

#### 4.2 Confluent Platform

```bash
kubectl apply -f confluent_platform.yaml -n $NAMESPACE
```

After that wait for the kafka-0 pod to be running and without errors.
```bash
kubectl get pods -n $NAMESPACE
```

#### 4.3 Endpoint

The bootstrap endpoint used in this deployment is a placeholder and will not resolve automatically. To ensure proper connectivity, you must manually register it in the `/etc/hosts` file. This involves mapping the bootstrap hostname to the appropriate IP address of your AKS cluster. Without this step, clients and components may fail to communicate with the Confluent Platform.

To know what is the external IP address assigned to the kafka-service, run the following command:
```bash
kubectl get svc -n $NAMESPACE
```

Response example:
```bash
NAME                 TYPE           CLUSTER-IP     EXTERNAL-IP     PORT(S)                                        AGE
confluent-operator   ClusterIP      10.0.234.251   <none>          7778/TCP                                       81m
kafka                ClusterIP      None           <none>          9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   68m
kafka-0-internal     ClusterIP      10.0.49.159    <none>          9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   68m
kafka-service        LoadBalancer   10.0.226.35    51.141.84.215   9092:32382/TCP                                 68m
```

For the example above, the following line needs to be added in the `/etc/hosts` file:
```bash
51.141.84.215    local.kafka.sainsburys 
```

Make sure the CP Kafka cluster has a SSL certificate attached to it:
```bash
openssl s_client -connect local.kafka.sainsburys:9092 -servername local.kafka.sainsburys
```

#### 4.4 Topics

This CRD can be used as a template for topics creation.

```bash
kubectl apply -f topic-demo.yaml -n $NAMESPACE
kubectl apply -f topic-catalina.yaml -n $NAMESPACE
```

Alternativelly, to create a topic using ``, try:
```bash
kafka-topics --create \
   --topic demo-topic \
  --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
   --partitions 1 \
   --replication-factor 1

kafka-topics --create \
   --topic catalina-test \
  --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
   --partitions 1 \
   --replication-factor 1
```

List topics:

The kafka CLI will only work with Java 17. If you have v21 installed, try setting it to v17 temporarely:
```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

List topics:
```bash
kafka-topics --list \
  --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties
```

Execute Performance Tests:
```bash
kafka-producer-perf-test \
   --topic demo-topic \
   --num-records 20000 \
   --record-size 10000 \
   --throughput -1 \
   --producer.config ./sslcli.properties \
   --producer-props bootstrap.servers=local.kafka.sainsburys:9092 batch.size=100
```

#### 4.5 ACLs

List ACLs:
```bash
kafka-acls --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
  --list
```

Add ACLs:
```bash
kafka-acls --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
  --add \
  --allow-principal "User:catalina-001" \
  --operation All \
  --topic 'catalina' \
  --resource-pattern-type prefixed \
  --group '*'

kafka-acls --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
  --add \
  --allow-principal "User:catalina-001" \
  --operation Describe \
  --cluster

kafka-acls --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
  --add \
  --allow-principal User:catalina-001 \
  --operation All \
  --group catalina-consumer-group
```

Consumer Test (Python):
```bash
python3 consumer.py
```

Producer Test (Python):
```bash
python3 producer.py
```

To remove the ACLs for a given user (see example for `catalina-001`):
```bash
kafka-acls --bootstrap-server $bootstrap \
  --command-config ./sslcli.properties \
  --remove \
  --allow-principal "User:catalina-001" \
  --group '*' \
  --force
```

## Tearing it down
```bash
NAMESPACE="sainsburys"
kubectl config set-context --current --namespace=$NAMESPACE
kubectl delete -f topic-catalina.yaml -n $NAMESPACE
kubectl delete -f topic-demo.yaml -n $NAMESPACE
kubectl delete -f confluent_platform.yaml -n $NAMESPACE
kubectl delete -f secrets.yaml -n $NAMESPACE
helm uninstall confluent-operator
```