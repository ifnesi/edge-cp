# Edge Confluent Platform - PoC

## 1. Requirements and Assumptions
- Embedded REST (v3). No REST Proxy (producers/consumers to use the Kafka protocol)
- No C3, ksqlDB, and Schema Registry
- High-Available Kafka Cluster 3x Kraft + 3x Confluent Servers on v7.9.0 (or latest)
  - 8 vCPU
  - 16 GB RAM
  - 5 TB disk (persistent storage, depending on a suitable Storage class)
  - One single cluster, no DR
- Single namespace containing the CfK Operator and the CP pod
- Separate namespace for monitoring (and potentially other agents Sainsbury’s may want to deploy)
- Self-signed TLS (auto-generated certs)
  - SASL_PLAINTEXT inside the pod (for CONTROLLER and REPLICATION listeners)
  - SASL_SSL outside the pod (for EXTERNAL listener)
  - SSL for Embedded REST (v3)
  - No SSL certificate rotation
- File-based user creds store (SASL_SSL with basic creds for external AuthN)
- Kafka ACLs, but no Confluent RBACs
- JMX exporter for Prometheus
- No need for the Confluent Metrics/Telemetry Reporter

## 2. Deploying the Edge-CP Platform

This deployment utilises [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) to apply the necessary CRD/YAML files for deploying Confluent Platform on Kubernetes. The target environment is **Azure Kubernetes Service (AKS)**. Before proceeding, ensure that kubectl is correctly configured to interact with your AKS cluster. This includes setting up kubectl with the appropriate Azure credentials and context.

### 2.1 Define Env Vars

```bash
export NAMESPACE="cp-poc"
export DOMAIN="local.kafka."$NAMESPACE
export REST_DOMAIN="kafka."$DOMAIN
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

To set the [Confluent Platform licence at a global level](https://docs.confluent.io/operator/current/co-license.html) use `--set licenseKey=<CFK license key>` when installing the `confluent-operator`. Also, make sute to set `spec.license.globalLicense: true` in the component custom resources (CR). That will create the confluent-operator-licensing secret with the following files:
 - `license.txt` contains the <CFK_license_key> you specified
 - `publicKey.pem` contains the public key used to validate the signed license

```bash
helm upgrade --install confluent-operator confluentinc/confluent-for-kubernetes \
  --namespace $NAMESPACE \
  --set kRaftEnabled=true #--set licenseKey=<CFK license key>
```

Confluent Platform Licences can also be installed at the [component-level](https://docs.confluent.io/operator/current/co-license.html#update-component-level-licenses).

Make sure the confluent-operator pod is running:
```bash
kubectl get pods -n $NAMESPACE
```

Response (example):
```bash
NAME                                 READY   STATUS    RESTARTS   AGE
confluent-operator-9876f6577-gwms5   1/1     Running   0          5s
```

### 2.4 Create SSL Self-Signed Certificate (Main Domain + wildcard for the SANs)

Make sure to have `openssl`, `cfssl` and `cfssljson` installed.

```bash
rm -rf $CERTS_FOLDER 2> /dev/null
mkdir $CERTS_FOLDER

echo "jksPassword="$JKS_PASSWORD | tr -d '\n' > $CERTS_FOLDER/jksPassword.txt

openssl genrsa -out $CERTS_FOLDER/rootCAkey.pem 2048
openssl req -x509  -new -nodes \
  -key $CERTS_FOLDER/rootCAkey.pem \
  -days 3650 \
  -out $CERTS_FOLDER/cacerts.pem \
  -subj "/C=US/ST=CA/L=MVT/O=TestOrg/OU=Cloud/CN=TestCA"
openssl x509 -in $CERTS_FOLDER/cacerts.pem -text -noout

keytool -delete -alias $NAMESPACE -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD 2> /dev/null
keytool -importcert -trustcacerts -alias $NAMESPACE -file $CERTS_FOLDER/cacerts.pem -keystore $CERTS_FOLDER/truststore.jks -storepass $JKS_PASSWORD -noprompt

cfssl gencert -ca=$CERTS_FOLDER/cacerts.pem \
  -ca-key=$CERTS_FOLDER/rootCAkey.pem \
  -config=ca-config.json \
  -profile=server kafka-server-domain.json | cfssljson -bare $CERTS_FOLDER/kafka-server

kubectl delete secret tls-kafka -n $NAMESPACE 2> /dev/null
kubectl create secret generic tls-kafka \
  --from-file=fullchain.pem=$CERTS_FOLDER/kafka-server.pem \
  --from-file=cacerts.pem=$CERTS_FOLDER/cacerts.pem \
  --from-file=privkey.pem=$CERTS_FOLDER/kafka-server-key.pem \
  --namespace $NAMESPACE

kubectl delete secret ca-pair-sslcerts -n $NAMESPACE 2> /dev/null
kubectl create secret generic ca-pair-sslcerts \
  --from-file=ca.crt=./sslcerts/cacerts.pem \
  --from-file=ca.key=./sslcerts/rootCAkey.pem \
  -n $NAMESPACE 

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

Make sure the KRaft + Kafka pods are running:
```bash
kubectl get pods -n $NAMESPACE
```

Response (example):
```bash
NAME                                 READY   STATUS     RESTARTS   AGE
confluent-operator-9876f6577-gwms5   1/1     Running    0          2m59s
kafka-0                              1/1     Running    0          89s
kafka-1                              1/1     Running    0          89s
kafka-2                              1/1     Running    0          89s
kraftcontroller-0                    1/1     Running    0          170s
kraftcontroller-1                    1/1     Running    0          170s
kraftcontroller-2                    1/1     Running    0          170s
```

#### 2.6.2 Endpoint

The bootstrap endpoint used in this deployment is a placeholder and will not resolve automatically. To ensure proper connectivity, you must manually register it in the `/etc/hosts` file. This involves mapping the bootstrap hostname to the appropriate IP address of your AKS cluster. Without this step, clients and components may fail to communicate with the Confluent Platform.

To know what are the external IP addresses assigned to the kafka cluster and brokers, run the following command:
```bash
kubectl get svc -n $NAMESPACE
```

Response (example):
```bash
NAME                            TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)                                                                   AGE
confluent-operator              ClusterIP      10.0.104.234   <none>           7778/TCP                                                                  4h19m
kafka                           ClusterIP      None           <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   47s
kafka-0-internal                ClusterIP      10.0.195.238   <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   47s
kafka-0-lb                      LoadBalancer   10.0.91.139    51.137.132.62    9092:31947/TCP                                                            47s
kafka-1-internal                ClusterIP      10.0.7.224     <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   47s
kafka-1-lb                      LoadBalancer   10.0.60.103    51.137.132.75    9092:32304/TCP                                                            47s
kafka-2-internal                ClusterIP      10.0.200.141   <none>           9074/TCP,9092/TCP,8090/TCP,9071/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP   47s
kafka-2-lb                      LoadBalancer   10.0.7.198     51.137.132.245   9092:31897/TCP                                                            47s
kafka-bootstrap-lb              LoadBalancer   10.0.84.162    51.137.157.215   9092:30812/TCP                                                            47s
kafka-kafka-rest-bootstrap-lb   LoadBalancer   10.0.78.63     51.137.155.27    8090:32524/TCP                                                            47s
kraftcontroller                 ClusterIP      None           <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              108s
kraftcontroller-0-internal      ClusterIP      10.0.105.126   <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              108s
kraftcontroller-1-internal      ClusterIP      10.0.9.181     <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              108s
kraftcontroller-2-internal      ClusterIP      10.0.32.9      <none>           9074/TCP,7203/TCP,7777/TCP,7778/TCP,9072/TCP                              108s
```

Alternatively, run the script `./etc_hosts.sh` to printout the entries required for `/etc/hosts`. See below example for a three brokers cluster:
```bash
# Entries for /etc/hosts:
51.137.132.62 b0.local.kafka.cp-poc
51.137.132.75 b1.local.kafka.cp-poc
51.137.132.245 b2.local.kafka.cp-poc
51.137.157.215 local.kafka.cp-poc
51.137.155.27 kafka.local.kafka.cp-poc
```

Make sure the CP Kafka cluster (Loadbalancer) has a SSL certificate attached to it:
```bash
openssl s_client -connect $BOOTSTRAP -servername $DOMAIN
```

To test access to the REST Interface (v3), try:
```bash
curl -v -k "https://$REST_DOMAIN:8090/kafka/v3/clusters" -u kafka:kafka-secret -H "Accept: application/json" | jq .
```

Response (example):
```bash
{
  "kind": "KafkaClusterList",
  "metadata": {
    "self": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters",
    "next": null
  },
  "data": [
    {
      "kind": "KafkaCluster",
      "metadata": {
        "self": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01",
        "resource_name": "crn:///kafka=ConfluentPlatformPoC01"
      },
      "cluster_id": "ConfluentPlatformPoC01",
      "controller": {
        "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/brokers/0"
      },
      "acls": {
        "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/acls"
      },
      "brokers": {
        "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/brokers"
      },
      "broker_configs": {
        "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/broker-configs"
      },
      "consumer_groups": {
        "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/consumer-groups"
      },
      "topics": {
        "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics"
      },
      "partition_reassignments": {
        "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics/-/partitions/-/reassignment"
      }
    }
  ]
}
```

#### 2.6.3 Topics

The kafka CLI will only work with Java 17. If you have v21 installed, try setting it to v17 temporarely:
```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

List topics (Kafka CLI):
```bash
kafka-topics --list \
  --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties
```

List topics via the [REST Admin v3 interface](https://docs.confluent.io/platform/current/kafka-rest/api.html#crest-api-v3):
```bash
curl -k "https://$REST_DOMAIN:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics" -u kafka:kafka-secret -H "Accept: application/json" | jq .
```

These CRDs can be used as a template for topics creation.

```bash
kubectl apply -f topic-demo.yaml -n $NAMESPACE
kubectl apply -f topic-catalina.yaml -n $NAMESPACE
```

Alternativelly, to create a topic using `kafka-topics(.sh)`, try:
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

The REST Admin v3 interface can also be used to create topics, for example:
```bash
curl -k -X POST "https://$REST_DOMAIN:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics" \
  -u kafka:kafka-secret \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"topic_name": "catalina-test-101", "partitions_count": 1, "replication_factor": 1, "configs": [{"name": "cleanup.policy", "value": "delete"}, {"name": "compression.type", "value": "gzip"}]}' \
  | jq .
```

Response (example):
```bash
{
  "kind": "KafkaTopic",
  "metadata": {
    "self": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics/catalina-test-101",
    "resource_name": "crn:///kafka=ConfluentPlatformPoC01/topic=catalina-test-101"
  },
  "cluster_id": "ConfluentPlatformPoC01",
  "topic_name": "catalina-test-101",
  "is_internal": false,
  "replication_factor": 1,
  "partitions_count": 1,
  "partitions": {
    "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics/catalina-test-101/partitions"
  },
  "configs": {
    "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics/catalina-test-101/configs"
  },
  "partition_reassignments": {
    "related": "https://kafka.local.kafka.cp-poc:8090/kafka/v3/clusters/ConfluentPlatformPoC01/topics/catalina-test-101/partitions/-/reassignment"
  },
  "authorized_operations": []
}
```

Execute Performance Tests:
```bash
kafka-producer-perf-test \
   --topic demo-topic \
   --num-records 20000 \
   --record-size 10000 \
   --throughput -1 \
   --producer.config ./sslcli.properties \
   --producer-props bootstrap.servers=$BOOTSTRAP batch.size=100 compression.type=lz4 acks=all
```

#### 2.6.4 ACLs

List ACLs (Kafka CLI):
```bash
kafka-acls --bootstrap-server $BOOTSTRAP \
  --command-config ./sslcli.properties \
  --list
```

List ACLs via the [REST Admin v3 interface](https://docs.confluent.io/platform/current/kafka-rest/api.html#crest-api-v3):
```bash
curl -k "https://$REST_DOMAIN:8090/kafka/v3/clusters/ConfluentPlatformPoC01/acls" -u kafka:kafka-secret -H "Accept: application/json" | jq .
```

Add ACLs (Kafka CLI):
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

The REST Admin v3 interface can also be used to create ACLs, for example:
```bash
curl -k -X POST "https://$REST_DOMAIN:8090/kafka/v3/clusters/ConfluentPlatformPoC01/acls:batch" \
  -u kafka:kafka-secret \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"data": [{"resource_type": "TOPIC", "resource_name": "demo-topic", "pattern_type": "LITERAL", "principal": "User:catalina-001", "host": "*", "operation": "ALL", "permission": "ALLOW"}]}' \
  | jq .
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

## 3. Observability with Prometheus-Grafana Stack
Deploy Prometheus and Grafana using Helm charts or Kubernetes manifests. You can use the following commands to install them via Helm:
```bash
helm install prometheus prometheus-community/kube-prometheus-stack
helm install grafana grafana/grafana
```

To expose Kafka metrics to Prometheus, you need to enable JMX Exporter. Kafka exposes metrics through JMX (Java Management Extensions). CFK supports JMX exporter integration out of the box.

Modify your Kafka deployment to include the JMX exporter:
```
spec:
  kafka:
    config:
      KAFKA_JMX_EXPORTER_ENABLED: "true"
      KAFKA_JMX_EXPORTER_PORT: "<PORT NUMBER>"
```

For docker based deployments here is an [example](./cp-observability/docker-compose.yml#L57C6-L57C16).</br>
Configure Prometheus to scrape Kafka metrics. This typically involves adding a scrape configuration in the Prometheus config to scrape the JMX exporter endpoint exposed by Kafka pods.

In the Prometheus configuration (prometheus.yaml), add the following scrape job:
```
scrape_configs:
  - job_name: 'kafka'
    static_configs:
      - targets: ['<kafka-pod-ip>:<PORT NUMBER AS IN THE PREV STEP>']
```

After Prometheus starts scraping metrics from Kafka, you can create Grafana dashboards to visualize those metrics.
You can either create your custom dashboards or use pre-built Kafka dashboards from the [jmx-monitoring-stack repository](https://github.com/confluentinc/jmx-monitoring-stacks/tree/main/jmxexporter-prometheus-grafana/assets/grafana/provisioning).

## 4. Tearing it down
```bash
kubectl delete -f topic-catalina.yaml -n $NAMESPACE
kubectl delete -f topic-demo.yaml -n $NAMESPACE
kubectl delete -f confluent_platform_HA.yaml -n $NAMESPACE
kubectl delete secret ca-pair-sslcerts -n $NAMESPACE
kubectl delete secrets credential -n $NAMESPACE
helm uninstall confluent-operator
helm uninstall prometheus
helm uninstall grafana
kubectl delete namespace $NAMESPACE
rm -rf $CERTS_FOLDER
```
