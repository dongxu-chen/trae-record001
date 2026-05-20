package com.configcenter.client;

import com.configcenter.protocol.*;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Closeable;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 配置中心客户端
 * 支持gRPC长连接订阅配置变更 + 主动拉取备选方案
 */
public class ConfigServiceClient implements Closeable {

    private static final Logger log = LoggerFactory.getLogger(ConfigServiceClient.class);

    private final String serverHost;
    private final int serverPort;
    private final String clientId;
    private final String serviceName;
    private final String namespace;
    private final String group;

    private ManagedChannel channel;
    private ConfigServiceGrpc.ConfigServiceStub asyncStub;
    private ConfigServiceGrpc.ConfigServiceBlockingStub blockingStub;

    private StreamObserver<SubscribeRequest> subscribeStream;
    private StreamObserver<HeartbeatRequest> heartbeatStream;

    private final Map<String, String> configCache = new ConcurrentHashMap<>();
    private final Map<String, Long> versionCache = new ConcurrentHashMap<>();
    private final List<ConfigChangeListener> changeListeners = new CopyOnWriteArrayList<>();

    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private final AtomicBoolean stopped = new AtomicBoolean(false);

    private final Set<String> subscribedDataIds = new HashSet<>();

    private ConfigServiceClient(Builder builder) {
        this.serverHost = builder.serverHost;
        this.serverPort = builder.serverPort;
        this.clientId = builder.clientId != null ? builder.clientId : generateClientId();
        this.serviceName = builder.serviceName;
        this.namespace = builder.namespace != null ? builder.namespace : "public";
        this.group = builder.group != null ? builder.group : "DEFAULT_GROUP";
    }

    public static Builder builder() {
        return new Builder();
    }

    /**
     * 启动客户端，建立gRPC连接
     */
    public synchronized void start() {
        if (stopped.get()) {
            throw new IllegalStateException("客户端已停止");
        }
        if (connected.get()) {
            return;
        }

        try {
            // 建立gRPC连接
            channel = ManagedChannelBuilder.forAddress(serverHost, serverPort)
                    .usePlaintext()
                    .keepAliveTime(30, TimeUnit.SECONDS)
                    .keepAliveTimeout(10, TimeUnit.SECONDS)
                    .build();

            asyncStub = ConfigServiceGrpc.newStub(channel);
            blockingStub = ConfigServiceGrpc.newBlockingStub(channel);

            // 启动心跳
            startHeartbeat();

            // 启动重连调度
            startReconnectScheduler();

            connected.set(true);
            log.info("配置中心客户端启动成功, clientId: {}, server: {}:{}",
                    clientId, serverHost, serverPort);
        } catch (Exception e) {
            log.error("配置中心客户端启动失败", e);
            throw new RuntimeException("配置中心客户端启动失败", e);
        }
    }

    /**
     * 订阅配置变更（长连接方式）
     */
    public void subscribe(String... dataIds) {
        checkStarted();

        for (String dataId : dataIds) {
            subscribedDataIds.add(dataId);
        }

        doSubscribe();
        log.info("已订阅配置变更, dataIds: {}", subscribedDataIds);
    }

    private void doSubscribe() {
        if (subscribedDataIds.isEmpty()) {
            return;
        }

        ClientInfo clientInfo = ClientInfo.newBuilder()
                .setClientId(clientId)
                .setServiceName(serviceName)
                .setNamespace(namespace)
                .setGroup(group)
                .setTimestamp(System.currentTimeMillis())
                .build();

        SubscribeRequest request = SubscribeRequest.newBuilder()
                .setClient(clientInfo)
                .addAllDataIds(subscribedDataIds)
                .putAllKnownVersions(versionCache)
                .build();

        asyncStub.subscribe(request, new StreamObserver<SubscribeResponse>() {
            @Override
            public void onNext(SubscribeResponse response) {
                handleConfigChange(response);
            }

            @Override
            public void onError(Throwable t) {
                log.warn("配置订阅连接异常，将尝试重连", t);
                connected.set(false);
            }

            @Override
            public void onCompleted() {
                log.info("配置订阅连接关闭");
                connected.set(false);
            }
        });
    }

    /**
     * 处理配置变更推送
     */
    private void handleConfigChange(SubscribeResponse response) {
        if (response.getStatus() != ResponseStatus.SUCCESS) {
            log.warn("收到非成功状态的配置变更通知: {}", response.getStatus());
            return;
        }

        String dataId = response.getDataId();
        long newVersion = response.getVersion();
        Long oldVersion = versionCache.get(dataId);

        if (oldVersion != null && oldVersion >= newVersion) {
            log.debug("配置版本未变化，忽略推送, dataId: {}, version: {}", dataId, newVersion);
            return;
        }

        // 应用配置变更
        List<ConfigChangeEvent.ChangeItem> changes = new ArrayList<>();
        for (ConfigItem item : response.getChangedItemsList()) {
            String key = item.getKey();
            String oldValue = configCache.get(key);
            String newValue = item.getChangeType() == ConfigChangeType.DELETED ? null : item.getValue();

            if (item.getChangeType() == ConfigChangeType.DELETED) {
                configCache.remove(key);
            } else {
                configCache.put(key, newValue);
            }

            changes.add(new ConfigChangeEvent.ChangeItem(
                    key, oldValue, newValue, convertChangeType(item.getChangeType())));
        }

        versionCache.put(dataId, newVersion);

        // 通知监听器
        if (!changes.isEmpty()) {
            ConfigChangeEvent event = new ConfigChangeEvent(dataId, response.getGroup(), changes);
            notifyListeners(event);
            log.info("配置变更已应用, dataId: {}, 变更数: {}", dataId, changes.size());
        }
    }

    private ConfigChangeEvent.ChangeType convertChangeType(ConfigChangeType type) {
        switch (type) {
            case ADDED: return ConfigChangeEvent.ChangeType.ADDED;
            case MODIFIED: return ConfigChangeEvent.ChangeType.MODIFIED;
            case DELETED: return ConfigChangeEvent.ChangeType.DELETED;
            default: return ConfigChangeEvent.ChangeType.MODIFIED;
        }
    }

    /**
     * 主动拉取配置（备选方案，当长连接不可用时使用）
     */
    public Map<String, String> pullConfig(String dataId, boolean fullPull) {
        checkStarted();

        ClientInfo clientInfo = ClientInfo.newBuilder()
                .setClientId(clientId)
                .setServiceName(serviceName)
                .setNamespace(namespace)
                .setGroup(group)
                .setTimestamp(System.currentTimeMillis())
                .build();

        PullConfigRequest request = PullConfigRequest.newBuilder()
                .setClient(clientInfo)
                .setDataId(dataId)
                .setGroup(group)
                .setKnownVersion(versionCache.getOrDefault(dataId, 0L))
                .setFullPull(fullPull)
                .build();

        try {
            PullConfigResponse response = blockingStub.pullConfig(request);

            if (response.getStatus() == ResponseStatus.NO_CHANGE) {
                log.debug("配置无变更, dataId: {}", dataId);
                return fullPull ? new HashMap<>(configCache) : Collections.emptyMap();
            }

            if (response.getStatus() != ResponseStatus.SUCCESS) {
                log.error("拉取配置失败, status: {}, message: {}", response.getStatus(), response.getMessage());
                throw new RuntimeException("拉取配置失败: " + response.getMessage());
            }

            // 应用全量配置
            if (fullPull && !response.getConfigDataMap().isEmpty()) {
                configCache.putAll(response.getConfigDataMap());
                versionCache.put(dataId, response.getVersion());
                log.info("全量配置拉取成功, dataId: {}, 配置数: {}", dataId, response.getConfigDataMap().size());
                return new HashMap<>(configCache);
            }

            // 应用增量变更
            if (!response.getChangedItemsList().isEmpty()) {
                List<ConfigChangeEvent.ChangeItem> changes = new ArrayList<>();
                for (ConfigItem item : response.getChangedItemsList()) {
                    String key = item.getKey();
                    String oldValue = configCache.get(key);
                    String newValue = item.getChangeType() == ConfigChangeType.DELETED ? null : item.getValue();

                    if (item.getChangeType() == ConfigChangeType.DELETED) {
                        configCache.remove(key);
                    } else {
                        configCache.put(key, newValue);
                    }

                    changes.add(new ConfigChangeEvent.ChangeItem(
                            key, oldValue, newValue, convertChangeType(item.getChangeType())));
                }

                versionCache.put(dataId, response.getVersion());
                notifyListeners(new ConfigChangeEvent(dataId, group, changes));
                log.info("增量配置拉取成功, dataId: {}, 变更数: {}", dataId, changes.size());
            }

            return new HashMap<>(configCache);

        } catch (Exception e) {
            log.error("拉取配置异常, dataId: {}", dataId, e);
            throw new RuntimeException("拉取配置失败", e);
        }
    }

    /**
     * 获取配置值
     */
    public String getConfig(String key) {
        return configCache.get(key);
    }

    /**
     * 获取配置值，带默认值
     */
    public String getConfig(String key, String defaultValue) {
        return configCache.getOrDefault(key, defaultValue);
    }

    /**
     * 获取所有配置
     */
    public Map<String, String> getAllConfigs() {
        return new HashMap<>(configCache);
    }

    /**
     * 添加配置变更监听器
     */
    public void addChangeListener(ConfigChangeListener listener) {
        changeListeners.add(listener);
    }

    /**
     * 移除配置变更监听器
     */
    public void removeChangeListener(ConfigChangeListener listener) {
        changeListeners.remove(listener);
    }

    private void notifyListeners(ConfigChangeEvent event) {
        for (ConfigChangeListener listener : changeListeners) {
            try {
                listener.onChange(event);
            } catch (Exception e) {
                log.error("配置变更监听器执行异常", e);
            }
        }
    }

    /**
     * 启动心跳保活
     */
    private void startHeartbeat() {
        heartbeatStream = asyncStub.heartbeat(new StreamObserver<HeartbeatResponse>() {
            @Override
            public void onNext(HeartbeatResponse response) {
                log.trace("收到心跳响应, serverId: {}", response.getServerId());
            }

            @Override
            public void onError(Throwable t) {
                log.warn("心跳连接异常", t);
                connected.set(false);
            }

            @Override
            public void onCompleted() {
                log.info("心跳连接关闭");
                connected.set(false);
            }
        });

        // 定时发送心跳
        scheduler.scheduleAtFixedRate(() -> {
            if (!stopped.get() && heartbeatStream != null) {
                try {
                    heartbeatStream.onNext(HeartbeatRequest.newBuilder()
                            .setClientId(clientId)
                            .setTimestamp(System.currentTimeMillis())
                            .build());
                } catch (Exception e) {
                    log.warn("发送心跳失败", e);
                }
            }
        }, 5, 30, TimeUnit.SECONDS);
    }

    /**
     * 启动重连调度
     */
    private void startReconnectScheduler() {
        scheduler.scheduleAtFixedRate(() -> {
            if (!stopped.get() && !connected.get()) {
                try {
                    log.info("尝试重新连接配置中心...");
                    reconnect();
                } catch (Exception e) {
                    log.warn("重连失败，下次继续尝试", e);
                }
            }
        }, 10, 10, TimeUnit.SECONDS);
    }

    private synchronized void reconnect() {
        if (connected.get()) {
            return;
        }

        try {
            // 关闭旧连接
            if (channel != null && !channel.isShutdown()) {
                channel.shutdownNow();
            }

            // 新建连接
            channel = ManagedChannelBuilder.forAddress(serverHost, serverPort)
                    .usePlaintext()
                    .keepAliveTime(30, TimeUnit.SECONDS)
                    .keepAliveTimeout(10, TimeUnit.SECONDS)
                    .build();

            asyncStub = ConfigServiceGrpc.newStub(channel);
            blockingStub = ConfigServiceGrpc.newBlockingStub(channel);

            // 重新订阅
            if (!subscribedDataIds.isEmpty()) {
                doSubscribe();
            }

            // 重启心跳
            startHeartbeat();

            connected.set(true);
            log.info("配置中心重连成功");
        } catch (Exception e) {
            log.error("重连失败", e);
            throw e;
        }
    }

    private void checkStarted() {
        if (!connected.get()) {
            throw new IllegalStateException("客户端未启动，请先调用 start() 方法");
        }
    }

    private String generateClientId() {
        return "client-" + UUID.randomUUID().toString().substring(0, 8);
    }

    @Override
    public synchronized void close() {
        stopped.set(true);
        connected.set(false);

        scheduler.shutdownNow();

        if (heartbeatStream != null) {
            try {
                heartbeatStream.onCompleted();
            } catch (Exception ignored) {}
        }

        if (channel != null && !channel.isShutdown()) {
            channel.shutdownNow();
            try {
                channel.awaitTermination(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        configCache.clear();
        versionCache.clear();
        changeListeners.clear();
        subscribedDataIds.clear();

        log.info("配置中心客户端已关闭, clientId: {}", clientId);
    }

    public boolean isConnected() {
        return connected.get() && !stopped.get();
    }

    public String getClientId() {
        return clientId;
    }

    /**
     * 构建器
     */
    public static class Builder {
        private String serverHost = "localhost";
        private int serverPort = 9090;
        private String clientId;
        private String serviceName = "unknown-service";
        private String namespace;
        private String group;

        public Builder serverHost(String serverHost) {
            this.serverHost = serverHost;
            return this;
        }

        public Builder serverPort(int serverPort) {
            this.serverPort = serverPort;
            return this;
        }

        public Builder clientId(String clientId) {
            this.clientId = clientId;
            return this;
        }

        public Builder serviceName(String serviceName) {
            this.serviceName = serviceName;
            return this;
        }

        public Builder namespace(String namespace) {
            this.namespace = namespace;
            return this;
        }

        public Builder group(String group) {
            this.group = group;
            return this;
        }

        public ConfigServiceClient build() {
            return new ConfigServiceClient(this);
        }
    }
}
