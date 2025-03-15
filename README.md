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

### 1. Create Env Vars and K8s Namespace

```bash
export bootstrap=local.kafka.sainsburys-poc:9092
export NAMESPACE="sainsburys-poc"
export CERTS_FOLDER=./sslcerts/
export CREDENTIALS_FOLDER=./credentials/
export JKS_PASSWORD=mystorepassword
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
mkdir $CERTS_FOLDER

openssl genrsa -out $CERTS_FOLDER/ca-key.pem 2048
openssl req -new -key $CERTS_FOLDER/ca-key.pem -x509 \
  -days 1000 \
  -out $CERTS_FOLDER/ca.pem \
  -subj "/C=US/ST=CA/L=MountainView/O=Kafka/OU=Broker/CN=TestCA" \
  -config openssl.cnf

openssl req -new -newkey rsa:2048 -nodes \
   -keyout $CERTS_FOLDER/kafka-key.pem \
   -out $CERTS_FOLDER/kafka-csr.pem \
   -config openssl.cnf
openssl x509 -req -in $CERTS_FOLDER/kafka-csr.pem \
   -CA $CERTS_FOLDER/ca.pem -CAkey $CERTS_FOLDER/ca-key.pem \
   -CAcreateserial -out $CERTS_FOLDER/kafka-cert.pem \
   -days 1000 -sha256 -extfile openssl.cnf \
   -extensions v3_req

kubectl delete secret ca-pair-sslcerts -n $NAMESPACE
kubectl create secret tls ca-pair-sslcerts \
   --cert=$CERTS_FOLDER/kafka-cert.pem \
   --key=$CERTS_FOLDER/kafka-key.pem \
   -n $NAMESPACE

keytool -list -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD

keytool -delete -alias $NAMESPACE -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD
keytool -importcert -alias $NAMESPACE -file $CERTS_FOLDER/ca.pem -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD -noprompt

keytool -list -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD
```

### 4. Credentials

The authentication credentials for Confluent Platform are managed via Kubernetes Secrets, as defined in the `secrets.yaml` file. If any changes are required—such as updating passwords, adding new users, or modifying existing credentials—the YAML file must be updated accordingly and reapplied using `kubectl apply -f`. Once the updated Secret is applied, the authentication configuration will be refreshed automatically, as per the `refresh_ms="3000"` setting in the listener configuration. This ensures that the system picks up changes within 3 seconds without requiring a manual restart.

```bash
kubectl delete secrets credential -n $NAMESPACE
kubectl create secret generic credential \
  --from-file=plain.txt=$CREDENTIALS_FOLDER/plain.txt \
  --from-file=plain-users.json=$CREDENTIALS_FOLDER/plain-users.json \
  --from-file=basic.txt=$CREDENTIALS_FOLDER/basic.txt -n $NAMESPACE
```

### 5. Apply CRDs

#### 5.1 Confluent Platform

```bash
kubectl apply -f confluent_platform_HA.yaml -n $NAMESPACE
```

After that wait for the kafka-0 pod to be running and without errors.
```bash
kubectl get pods -n $NAMESPACE
```

#### 5.2 Endpoint

The bootstrap endpoint used in this deployment is a placeholder and will not resolve automatically. To ensure proper connectivity, you must manually register it in the `/etc/hosts` file. This involves mapping the bootstrap hostname to the appropriate IP address of your AKS cluster. Without this step, clients and components may fail to communicate with the Confluent Platform.

To know what are the external IP addresses assigned to the kafka cluster and brokers, run the following command:
```bash
kubectl get svc -n $NAMESPACE
```

Response example:
```bash
NAME                            TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)                                                                   AGE
confluent-operator              ClusterIP      10.0.178.252   <none>           7778/TCP                                                                  21m
kafka                           ClusterIP      None           <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   20m
kafka-0-internal                ClusterIP      10.0.116.145   <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   20m
kafka-0-lb                      LoadBalancer   10.0.13.7      51.137.148.94    9092:31041/TCP                                                            20m
kafka-1-internal                ClusterIP      10.0.79.150    <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   20m
kafka-1-lb                      LoadBalancer   10.0.119.51    51.137.149.119   9092:32083/TCP                                                            20m
kafka-2-internal                ClusterIP      10.0.109.138   <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   20m
kafka-2-lb                      LoadBalancer   10.0.6.107     51.137.158.253   9092:30770/TCP                                                            20m
kafka-bootstrap-lb              LoadBalancer   10.0.212.180   51.137.145.178   9092:30828/TCP                                                            20m
kafka-kafka-rest-bootstrap-lb   LoadBalancer   10.0.94.210    20.162.17.222    8090:32708/TCP                                                            20m
kraftcontroller                 ClusterIP      None           <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              21m
kraftcontroller-0-internal      ClusterIP      10.0.17.236    <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              21m
kraftcontroller-1-internal      ClusterIP      10.0.50.93     <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              21m
kraftcontroller-2-internal      ClusterIP      10.0.31.11     <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              21m
```

Alternatively, run the script `etc_hosts.sh` to printout the entries required for `/etc/hosts`. See below example for a three brokers cluster:
```bash
# Entries for /etc/hosts:
51.137.148.94 b0.local.kafka.sainsburys-poc
51.137.149.119 b1.local.kafka.sainsburys-poc
51.137.158.253 b2.local.kafka.sainsburys-poc
51.137.145.178 local.kafka.sainsburys-poc
20.162.17.222 kafka.local.kafka.sainsburys-poc
```

Make sure the CP Kafka cluster (Loadbalancer) has a SSL certificate attached to it:
```bash
openssl s_client -connect local.kafka.sainsburys-poc:9092 -servername local.kafka.sainsburys-poc
```

#### 5.3 Topics

These CRDs can be used as a template for topics creation.

```bash
kubectl apply -f topic-demo.yaml -n $NAMESPACE
kubectl apply -f topic-catalina.yaml -n $NAMESPACE
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

Execute Performance Tests:
```bash
kafka-producer-perf-test \
   --topic demo-topic \
   --num-records 20000 \
   --record-size 10000 \
   --throughput -1 \
   --producer.config ./sslcli.properties \
   --producer-props bootstrap.servers=local.kafka.sainsburys-poc:9092 batch.size=100 compression.type=lz4
```

#### 5.4 ACLs

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
kubectl delete -f topic-catalina.yaml -n $NAMESPACE
kubectl delete -f topic-demo.yaml -n $NAMESPACE
kubectl delete -f confluent_platform_HA.yaml -n $NAMESPACE
helm uninstall confluent-operator
kubectl delete namespace $NAMESPACE
rm -rf $CERTS_FOLDER
```