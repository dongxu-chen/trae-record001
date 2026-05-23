# 分布式锁服务 - 高可用部署指南

## 架构概述

本分布式锁服务采用以下架构实现高可用：

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│  (Java SDK with Circuit Breaker + Retry + Load Balancing)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        gRPC Load Balancer                        │
│                     (e.g., Nginx, Envoy, k8s Service)            │
└──────────────┬──────────────────┬──────────────────┬────────────┘
               │                  │                  │
               ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Lock Server #1   │ │  Lock Server #2   │ │  Lock Server #3   │
│  (gRPC + etcd)    │ │  (gRPC + etcd)    │ │  (gRPC + etcd)    │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                ┌───────────────────────────┐
                │      etcd Cluster         │
                │  (3+ nodes for HA)        │
                │  - Node 1                 │
                │  - Node 2                 │
                │  - Node 3                 │
                └───────────────────────────┘
```

## 1. etcd 集群部署

### 1.1 部署要求
- **节点数量**: 最少3个节点（推荐奇数个节点，3/5/7）
- **内存**: 每个节点至少2GB
- **CPU**: 每个节点至少2核
- **磁盘**: SSD，至少20GB

### 1.2 Docker Compose 部署 (测试环境)

创建 `docker-compose-etcd.yml`:

```yaml
version: '3.8'

services:
  etcd1:
    image: quay.io/coreos/etcd:v3.5.9
    container_name: etcd1
    ports:
      - "2379:2379"
      - "2380:2380"
    environment:
      - ETCD_NAME=etcd1
      - ETCD_INITIAL_ADVERTISE_PEER_URLS=http://etcd1:2380
      - ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd1:2379
      - ETCD_INITIAL_CLUSTER=etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      - ETCD_INITIAL_CLUSTER_TOKEN=etcd-cluster-1
      - ETCD_INITIAL_CLUSTER_STATE=new
    volumes:
      - etcd1-data:/etcd-data

  etcd2:
    image: quay.io/coreos/etcd:v3.5.9
    container_name: etcd2
    ports:
      - "22379:2379"
      - "22380:2380"
    environment:
      - ETCD_NAME=etcd2
      - ETCD_INITIAL_ADVERTISE_PEER_URLS=http://etcd2:2380
      - ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd2:2379
      - ETCD_INITIAL_CLUSTER=etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      - ETCD_INITIAL_CLUSTER_TOKEN=etcd-cluster-1
      - ETCD_INITIAL_CLUSTER_STATE=new
    volumes:
      - etcd2-data:/etcd-data

  etcd3:
    image: quay.io/coreos/etcd:v3.5.9
    container_name: etcd3
    ports:
      - "32379:2379"
      - "32380:2380"
    environment:
      - ETCD_NAME=etcd3
      - ETCD_INITIAL_ADVERTISE_PEER_URLS=http://etcd3:2380
      - ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd3:2379
      - ETCD_INITIAL_CLUSTER=etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      - ETCD_INITIAL_CLUSTER_TOKEN=etcd-cluster-1
      - ETCD_INITIAL_CLUSTER_STATE=new
    volumes:
      - etcd3-data:/etcd-data

volumes:
  etcd1-data:
  etcd2-data:
  etcd3-data:
```

启动命令：
```bash
docker-compose -f docker-compose-etcd.yml up -d
```

验证集群状态：
```bash
docker exec etcd1 etcdctl member list
docker exec etcd1 etcdctl endpoint health
```

## 2. 分布式锁服务部署

### 2.1 构建项目

```bash
# 首先编译生成gRPC代码
cd distributed-lock-common
mvn clean compile

# 然后构建整个项目
cd ..
mvn clean package -DskipTests
```

### 2.2 Dockerfile

创建 `Dockerfile`:

```dockerfile
FROM openjdk:11-jre-slim

WORKDIR /app

COPY distributed-lock-server/target/distributed-lock-server-*.jar /app/lock-server.jar

EXPOSE 50051

ENV ETCD_ENDPOINTS="http://etcd1:2379,http://etcd2:2379,http://etcd3:2379"
ENV GRPC_PORT=50051
ENV LEASE_TTL_SECONDS=30

CMD ["java", "-jar", "lock-server.jar"]
```

构建镜像：
```bash
docker build -t distributed-lock-server:1.0.0 .
```

### 2.3 Docker Compose 部署锁服务

创建 `docker-compose-lock.yml`:

```yaml
version: '3.8'

services:
  lock-server1:
    image: distributed-lock-server:1.0.0
    container_name: lock-server1
    ports:
      - "50051:50051"
    environment:
      - ETCD_ENDPOINTS=http://etcd1:2379,http://etcd2:2379,http://etcd3:2379
      - GRPC_PORT=50051
      - LEASE_TTL_SECONDS=30
    depends_on:
      - etcd1
      - etcd2
      - etcd3

  lock-server2:
    image: distributed-lock-server:1.0.0
    container_name: lock-server2
    ports:
      - "50052:50051"
    environment:
      - ETCD_ENDPOINTS=http://etcd1:2379,http://etcd2:2379,http://etcd3:2379
      - GRPC_PORT=50051
      - LEASE_TTL_SECONDS=30
    depends_on:
      - etcd1
      - etcd2
      - etcd3

  lock-server3:
    image: distributed-lock-server:1.0.0
    container_name: lock-server3
    ports:
      - "50053:50051"
    environment:
      - ETCD_ENDPOINTS=http://etcd1:2379,http://etcd2:2379,http://etcd3:2379
      - GRPC_PORT=50051
      - LEASE_TTL_SECONDS=30
    depends_on:
      - etcd1
      - etcd2
      - etcd3

  nginx-lb:
    image: nginx:1.25
    container_name: nginx-lb
    ports:
      - "8080:8080"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - lock-server1
      - lock-server2
      - lock-server3
```

### 2.4 Nginx gRPC 负载均衡配置

创建 `nginx.conf`:

```nginx
user nginx;
worker_processes auto;

error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    upstream grpc_servers {
        server lock-server1:50051;
        server lock-server2:50051;
        server lock-server3:50051;
        
        least_conn;
        keepalive 32;
    }

    server {
        listen 8080 http2;
        
        location / {
            grpc_pass grpc://grpc_servers;
            
            grpc_set_header Host $host;
            grpc_set_header X-Real-IP $remote_addr;
            grpc_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            grpc_set_header X-Forwarded-Proto $scheme;
            
            grpc_connect_timeout 5s;
            grpc_read_timeout 300s;
            grpc_send_timeout 300s;
        }
    }
}
```

## 3. Kubernetes 部署 (生产环境)

### 3.1 etcd Operator 部署

使用 etcd Operator 部署高可用 etcd 集群：

```yaml
apiVersion: etcd.database.coreos.com/v1beta2
kind: EtcdCluster
metadata:
  name: etcd-cluster
spec:
  size: 3
  version: "3.5.9"
  pod:
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "2"
        memory: "2Gi"
    persistentVolumeClaimSpec:
      storageClassName: "fast-ssd"
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 50Gi
```

### 3.2 锁服务 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: distributed-lock-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: distributed-lock-server
  template:
    metadata:
      labels:
        app: distributed-lock-server
    spec:
      containers:
      - name: lock-server
        image: distributed-lock-server:1.0.0
        ports:
        - containerPort: 50051
        env:
        - name: ETCD_ENDPOINTS
          value: "http://etcd-cluster-client:2379"
        - name: GRPC_PORT
          value: "50051"
        - name: LEASE_TTL_SECONDS
          value: "30"
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "1"
            memory: "512Mi"
        livenessProbe:
          grpc:
            port: 50051
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          grpc:
            port: 50051
          initialDelaySeconds: 5
          periodSeconds: 10
```

### 3.3 gRPC Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: distributed-lock-service
spec:
  type: ClusterIP
  ports:
  - port: 50051
    targetPort: 50051
    protocol: TCP
    name: grpc
  selector:
    app: distributed-lock-server
```

### 3.4 水平 Pod 自动扩缩容 (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: distributed-lock-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: distributed-lock-server
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 4. 监控配置

### 4.1 Prometheus 指标

部署 Prometheus 监控 gRPC 和 etcd 指标。

### 4.2 健康检查脚本

```bash
#!/bin/bash
# health-check.sh

GRPC_HEALTH_PROBE=/usr/local/bin/grpc_health_probe

$GRPC_HEALTH_PROBE -addr=localhost:50051 || exit 1
```

## 5. 配置参数说明

### 5.1 服务端配置

| 参数 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| etcd端点 | ETCD_ENDPOINTS | http://localhost:2379 | etcd集群地址，逗号分隔 |
| gRPC端口 | GRPC_PORT | 50051 | gRPC服务监听端口 |
| 租约TTL | LEASE_TTL_SECONDS | 30 | 锁租约过期时间(秒) |
| 自动续期 | - | true | 是否自动续期 |
| 续期间隔 | - | 10 | 租约续期间隔(秒) |

### 5.2 客户端配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 重试次数 | 3 | 失败重试最大次数 |
| 重试间隔 | 500ms | 重试等待时间 |
| 熔断阈值 | 50% | 失败率阈值 |
| 熔断恢复时间 | 10s | 熔断后恢复等待时间 |
| 连接超时 | 30s | 连接超时时间 |

## 6. 故障转移测试

### 6.1 etcd 节点故障

1. 停止一个etcd节点
2. 验证锁服务仍然正常工作
3. 检查集群自动恢复

### 6.2 锁服务节点故障

1. 停止一个锁服务实例
2. 验证客户端自动重连到其他节点
3. 验证负载均衡器自动移除故障节点

## 7. 性能优化建议

1. **etcd 调优**:
   - 使用SSD存储
   - 调整etcd压缩参数
   - 启用快照功能

2. **gRPC 调优**:
   - 调整连接池大小
   - 启用keepalive
   - 调整流控窗口

3. **JVM 调优**:
   - 使用G1垃圾回收器
   - 调整堆内存大小
   - 启用JMX监控

## 8. 安全建议

1. **启用TLS**:
   - 配置gRPC TLS加密
   - 配置etcd客户端认证

2. **访问控制**:
   - 实现API认证
   - 限制客户端IP访问

3. **网络安全**:
   - 使用网络隔离
   - 配置防火墙规则