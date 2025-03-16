# Edge Confluent Platform

## 1. Requirements and Assumptions
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

## 2. Deploying the Edge-CP Platform

This deployment utilises [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) to apply the necessary CRD/YAML files for deploying Confluent Platform on Kubernetes. The target environment is **Azure Kubernetes Service (AKS)**. Before proceeding, ensure that kubectl is correctly configured to interact with your AKS cluster. This includes setting up kubectl with the appropriate Azure credentials and context.

### 2.1 Define Env Vars

```bash
export NAMESPACE="sainsburys-poc"
export DOMAIN="local.kafka."$NAMESPACE
export BOOTSTRAP=$DOMAIN":9092"
export CERTS_FOLDER="./sslcerts/"
export CREDENTIALS_FOLDER="./credentials/"
export JKS_PASSWORD="mystorepassword"
```

### 2.2 Create K8s Namespace

```bash
kubectl create namespace $NAMESPACE 2> /dev/null
kubectl config set-context --current --namespace=$NAMESPACE
```

### 2.3 Install Confluent Operator

```bash
helm upgrade --install confluent-operator confluentinc/confluent-for-kubernetes \
  --namespace $NAMESPACE \
  --set kRaftEnabled=true #--set licenseKey=<CFK license key>
```

### 2.4 Create SSL Self-Signed Certificate

```bash
rm -rf $CERTS_FOLDER 2> /dev/null
mkdir $CERTS_FOLDER

openssl genrsa -out $CERTS_FOLDER/ca-key.pem 2048
openssl req -new -key $CERTS_FOLDER/ca-key.pem -x509 \
  -days 1000 \
  -out $CERTS_FOLDER/ca.pem \
  -subj "/C=GB/ST=GreaterLondon/L=London/O=Sainsburys/OU=Engineering/CN="$DOMAIN \
  -addext "subjectAltName = DNS:"$DOMAIN", DNS:*."$DOMAIN

kubectl delete secret ca-pair-sslcerts -n $NAMESPACE 2> /dev/null
kubectl create secret tls ca-pair-sslcerts \
   --cert=$CERTS_FOLDER/ca.pem \
   --key=$CERTS_FOLDER/ca-key.pem \
   -n $NAMESPACE

keytool -delete -alias $NAMESPACE -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD 2> /dev/null
keytool -importcert -alias $NAMESPACE -file $CERTS_FOLDER/ca.pem -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD -noprompt
keytool -list -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD
```

### 2.5 Credentials

The authentication credentials for Confluent Platform are managed via Kubernetes Secrets, as defined in the `secrets.yaml` file. If any changes are required—such as updating passwords, adding new users, or modifying existing credentials—the YAML file must be updated accordingly and reapplied using `kubectl apply -f`. Once the updated Secret is applied, the authentication configuration will be refreshed automatically, as per the `refresh_ms="3000"` setting in the listener configuration. This ensures that the system picks up changes within 3 seconds without requiring a manual restart.

```bash
kubectl delete secrets credential -n $NAMESPACE 2> /dev/null
kubectl create secret generic credential \
  --from-file=plain.txt=$CREDENTIALS_FOLDER/plain.txt \
  --from-file=plain-users.json=$CREDENTIALS_FOLDER/plain-users.json \
  --from-file=basic.txt=$CREDENTIALS_FOLDER/basic.txt -n $NAMESPACE
```

### 2.6 Apply CRDs

#### 2.6.1 Confluent Platform

```bash
kubectl apply -f confluent_platform_HA.yaml -n $NAMESPACE
```

After that wait for the kafka-0 pod to be running and without errors.
```bash
kubectl get pods -n $NAMESPACE
```

#### 2.6.2 Endpoint

The bootstrap endpoint used in this deployment is a placeholder and will not resolve automatically. To ensure proper connectivity, you must manually register it in the `/etc/hosts` file. This involves mapping the bootstrap hostname to the appropriate IP address of your AKS cluster. Without this step, clients and components may fail to communicate with the Confluent Platform.

To know what are the external IP addresses assigned to the kafka cluster and brokers, run the following command:
```bash
kubectl get svc -n $NAMESPACE
```

Response example:
```bash
NAME                         TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)                                                                   AGE
confluent-operator           ClusterIP      10.0.119.133   <none>           7778/TCP                                                                  137m
kafka                        ClusterIP      None           <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   80s
kafka-0-internal             ClusterIP      10.0.14.31     <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   80s
kafka-0-lb                   LoadBalancer   10.0.195.161   51.137.148.45    9092:31329/TCP                                                            80s
kafka-1-internal             ClusterIP      10.0.92.38     <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   80s
kafka-1-lb                   LoadBalancer   10.0.131.29    51.137.148.244   9092:31010/TCP                                                            80s
kafka-2-internal             ClusterIP      10.0.122.89    <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   80s
kafka-2-lb                   LoadBalancer   10.0.67.39     51.137.145.178   9092:32329/TCP                                                            80s
kafka-bootstrap-lb           LoadBalancer   10.0.82.251    51.137.150.177   9092:30994/TCP                                                            80s
kraftcontroller              ClusterIP      None           <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              2m21s
kraftcontroller-0-internal   ClusterIP      10.0.120.25    <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              2m21s
kraftcontroller-1-internal   ClusterIP      10.0.8.218     <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              2m21s
kraftcontroller-2-internal   ClusterIP      10.0.12.17     <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              2m21s
```

Alternatively, run the script `etc_hosts.sh` to printout the entries required for `/etc/hosts`. See below example for a three brokers cluster:
```bash
# Entries for /etc/hosts:
51.137.148.45 b0.local.kafka.sainsburys-poc
51.137.148.244 b1.local.kafka.sainsburys-poc
51.137.145.178 b2.local.kafka.sainsburys-poc
51.137.150.177 local.kafka.sainsburys-poc
```

Make sure the CP Kafka cluster (Loadbalancer) has a SSL certificate attached to it:
```bash
openssl s_client -connect local.kafka.sainsburys-poc:9092 -servername local.kafka.sainsburys-poc
```

#### 2.6.3 Topics

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
  --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties
```

Alternativelly, to create a topic using ``, try:
```bash
kafka-topics --create \
  --topic demo-topic \
  --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties \
  --partitions 1 \
  --replication-factor 1

kafka-topics --create \
  --topic catalina-test \
  --bootstrap-server $BOOTSTRAP \
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
   --producer-props bootstrap.servers=$BOOTSTRAP batch.size=100 compression.type=lz4
```

#### 2.6.4 ACLs

List ACLs:
```bash
kafka-acls --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties \
  --list
```

Add ACLs:
```bash
kafka-acls --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties \
  --add \
  --allow-principal "User:catalina-001" \
  --operation All \
  --topic 'catalina' \
  --resource-pattern-type prefixed \
  --group '*'

kafka-acls --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties \
  --add \
  --allow-principal "User:catalina-001" \
  --operation Describe \
  --cluster

kafka-acls --bootstrap-server $BOOTSTRAP \
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
kafka-acls --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties \
  --remove \
  --allow-principal "User:catalina-001" \
  --group '*' \
  --force
```

## 3. Tearing it down
```bash
kubectl delete -f topic-catalina.yaml -n $NAMESPACE
kubectl delete -f topic-demo.yaml -n $NAMESPACE
kubectl delete -f confluent_platform_HA.yaml -n $NAMESPACE
kubectl delete secret ca-pair-sslcerts -n $NAMESPACE
kubectl delete secrets credential -n $NAMESPACE
helm uninstall confluent-operator
kubectl delete namespace $NAMESPACE
rm -rf $CERTS_FOLDER
```