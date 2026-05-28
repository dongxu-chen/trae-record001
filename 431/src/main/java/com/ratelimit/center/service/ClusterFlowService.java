package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.cluster.ClusterStateManager;
import com.alibaba.csp.sentinel.cluster.client.config.ClusterClientConfig;
import com.alibaba.csp.sentinel.cluster.client.config.ClusterClientConfigManager;
import com.alibaba.csp.sentinel.cluster.server.config.ClusterServerConfigManager;
import com.alibaba.csp.sentinel.cluster.server.config.ServerFlowConfig;
import com.alibaba.csp.sentinel.cluster.server.config.ServerTransportConfig;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.ratelimit.center.common.RateLimitConstants;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.InetAddress;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
public class ClusterFlowService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Value("${rate-limit.cluster.enabled:true}")
    private boolean clusterEnabled;

    @Value("${rate-limit.cluster.server-port:18730}")
    private int serverPort;

    @Value("${rate-limit.cluster.token-server-host:127.0.0.1}")
    private String tokenServerHost;

    @Value("${rate-limit.cluster.datacenter:default}")
    private String currentDc;

    @Value("${rate-limit.cluster.total-quota:10000}")
    private int totalQuota;

    @Value("${server.port:8090}")
    private int appPort;

    private String nodeId;

    private final Map<String, Integer> clientTokenMap = new ConcurrentHashMap<>();

    private final Map<String, DcQuota> dcQuotaMap = new ConcurrentHashMap<>();

    private final Map<String, AtomicLong> localUsageMap = new ConcurrentHashMap<>();

    private final Map<String, AtomicInteger> borrowedQuotaMap = new ConcurrentHashMap<>();

    @Data
    public static class DcQuota {
        private String dc;
        private int totalQuota;
        private int allocatedQuota;
        private int usedQuota;
        private int availableQuota;
        private long timestamp;
        private Set<String> nodes = new HashSet<>();

        public int calculateQuotaForNode(int nodeCount) {
            if (nodeCount <= 0) return totalQuota;
            return totalQuota / nodeCount;
        }
    }

    @PostConstruct
    public void init() {
        try {
            nodeId = currentDc + "-" + InetAddress.getLocalHost().getHostAddress() + ":" + appPort;
        } catch (Exception e) {
            nodeId = currentDc + "-" + UUID.randomUUID().toString().substring(0, 8);
        }

        if (!clusterEnabled) {
            log.info("Cluster flow control is disabled");
            return;
        }

        try {
            initClusterServer();
            initClusterClient();
            scheduleClusterStateSync();
            scheduleQuotaCheck();
            log.info("Cluster flow control initialized, DC: {}, node: {}, mode: TOKEN_SERVER, port: {}",
                    currentDc, nodeId, serverPort);
        } catch (Exception e) {
            log.error("Failed to initialize cluster flow control", e);
        }
    }

    private void initClusterServer() {
        ClusterServerConfigManager.loadGlobalFlowConfig(
                new ServerFlowConfig()
                        .setExceedCount(1.0d)
                        .setMaxOccupyRatio(0.8d)
                        .setIntervalMs(1000)
        );

        ClusterServerConfigManager.loadServerTransportConfig(
                new ServerTransportConfig()
                        .setPort(serverPort)
                        .setIdleSeconds(600)
        );

        ClusterStateManager.applyState(ClusterStateManager.CLUSTER_SERVER);
    }

    private void initClusterClient() {
        ClusterClientConfigManager.applyNewConfig(
                new ClusterClientConfig()
                        .setRequestTimeout(500)
        );
    }

    private void scheduleClusterStateSync() {
        Thread syncThread = new Thread(() -> {
            while (true) {
                try {
                    syncClusterState();
                    TimeUnit.SECONDS.sleep(30);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.error("Failed to sync cluster state", e);
                }
            }
        }, "cluster-state-sync");
        syncThread.setDaemon(true);
        syncThread.start();
    }

    private void scheduleQuotaCheck() {
        Thread checkThread = new Thread(() -> {
            while (true) {
                try {
                    checkAndRebalanceQuota();
                    TimeUnit.SECONDS.sleep(60);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.error("Failed to check quota", e);
                }
            }
        }, "cluster-quota-check");
        checkThread.setDaemon(true);
        checkThread.start();
    }

    private void syncClusterState() {
        String dcKey = RateLimitConstants.REDIS_CLUSTER_DC_KEY + ":" + currentDc;
        String serverKey = dcKey + ":server";
        stringRedisTemplate.opsForValue().set(
                serverKey,
                tokenServerHost + ":" + serverPort,
                60,
                TimeUnit.SECONDS
        );

        String clientKey = dcKey + ":clients";
        stringRedisTemplate.opsForSet().add(clientKey, nodeId);
        stringRedisTemplate.expire(clientKey, 60, TimeUnit.SECONDS);

        syncQuotaToRedis();
    }

    private void syncQuotaToRedis() {
        try {
            String quotaKey = RateLimitConstants.REDIS_CLUSTER_DC_QUOTA_KEY + ":" + currentDc;

            DcQuota dcQuota = new DcQuota();
            dcQuota.setDc(currentDc);
            dcQuota.setTotalQuota(totalQuota);
            dcQuota.setAllocatedQuota(calculateAllocatedQuota());
            dcQuota.setUsedQuota(calculateTotalUsedQuota());
            dcQuota.setAvailableQuota(dcQuota.getAllocatedQuota() - dcQuota.getUsedQuota());
            dcQuota.setTimestamp(System.currentTimeMillis());
            dcQuota.setNodes(getClusterClients());

            String usageKey = RateLimitConstants.REDIS_CLUSTER_DC_USAGE_KEY + ":" + currentDc;
            Map<String, Long> usageSnapshot = new HashMap<>();
            localUsageMap.forEach((k, v) -> usageSnapshot.put(k, v.get()));

            stringRedisTemplate.opsForValue().set(quotaKey, JSON.toJSONString(dcQuota), 60, TimeUnit.SECONDS);
            stringRedisTemplate.opsForValue().set(usageKey, JSON.toJSONString(usageSnapshot), 60, TimeUnit.SECONDS);

            dcQuotaMap.put(currentDc, dcQuota);
        } catch (Exception e) {
            log.error("Failed to sync quota to Redis", e);
        }
    }

    private int calculateAllocatedQuota() {
        int allocated = 0;
        for (AtomicInteger quota : borrowedQuotaMap.values()) {
            allocated += quota.get();
        }
        return totalQuota + allocated;
    }

    private int calculateTotalUsedQuota() {
        return localUsageMap.values().stream()
                .mapToInt(v -> (int) v.get())
                .sum();
    }

    private void checkAndRebalanceQuota() {
        try {
            Set<String> allDcs = getAllDcs();
            for (String dc : allDcs) {
                DcQuota remoteQuota = getDcQuotaFromRedis(dc);
                if (remoteQuota != null) {
                    dcQuotaMap.put(dc, remoteQuota);
                }
            }

            DcQuota localQuota = dcQuotaMap.get(currentDc);
            if (localQuota != null) {
                int localAvailable = localQuota.getAvailableQuota();
                int localUsed = localQuota.getUsedQuota();
                int localAllocated = localQuota.getAllocatedQuota();

                if (localUsed > localAllocated * 0.9) {
                    borrowQuotaFromOtherDcs();
                } else if (localAvailable > localAllocated * 0.3 && !borrowedQuotaMap.isEmpty()) {
                    returnBorrowedQuota();
                }
            }
        } catch (Exception e) {
            log.error("Failed to rebalance quota", e);
        }
    }

    private void borrowQuotaFromOtherDcs() {
        for (Map.Entry<String, DcQuota> entry : dcQuotaMap.entrySet()) {
            if (entry.getKey().equals(currentDc)) continue;

            DcQuota remoteQuota = entry.getValue();
            int borrowable = (int) (remoteQuota.getAvailableQuota() * (RateLimitConstants.CLUSTER_QUOTA_BORROW_PERCENT / 100.0));

            if (borrowable > 0) {
                borrowedQuotaMap.merge(remoteQuota.getDc(), new AtomicInteger(borrowable), (old, newVal) -> {
                    old.addAndGet(newVal.get());
                    return old;
                });

                log.info("Borrowed {} quota from DC: {}", borrowable, remoteQuota.getDc());
            }
        }
    }

    private void returnBorrowedQuota() {
        borrowedQuotaMap.clear();
        log.info("Returned all borrowed quota");
    }

    public int requestLocalQuota(String resource, int requestedTokens) {
        DcQuota localQuota = dcQuotaMap.get(currentDc);
        if (localQuota == null) return requestedTokens;

        int available = localQuota.getAvailableQuota();
        int granted = Math.min(requestedTokens, available);

        localUsageMap.computeIfAbsent(resource, k -> new AtomicLong(0))
                .addAndGet(granted);

        clientTokenMap.merge(resource, granted, Integer::sum);

        return granted;
    }

    public boolean tryAcquire(String resource, int tokenCount) {
        int granted = requestLocalQuota(resource, tokenCount);
        return granted >= tokenCount;
    }

    public void releaseQuota(String resource, int tokenCount) {
        localUsageMap.computeIfPresent(resource, (k, v) -> {
            long newValue = v.get() - tokenCount;
            return new AtomicLong(Math.max(0, newValue));
        });
    }

    public DcQuota getCurrentDcQuota() {
        return dcQuotaMap.get(currentDc);
    }

    public Map<String, DcQuota> getAllDcQuotas() {
        for (String dc : getAllDcs()) {
            DcQuota quota = getDcQuotaFromRedis(dc);
            if (quota != null) {
                dcQuotaMap.put(dc, quota);
            }
        }
        return new ConcurrentHashMap<>(dcQuotaMap);
    }

    private Set<String> getAllDcs() {
        Set<String> dcs = new HashSet<>();
        try {
            Set<String> keys = stringRedisTemplate.keys(RateLimitConstants.REDIS_CLUSTER_DC_QUOTA_KEY + ":*");
            if (keys != null) {
                for (String key : keys) {
                    String dc = key.substring((RateLimitConstants.REDIS_CLUSTER_DC_QUOTA_KEY + ":").length());
                    dcs.add(dc);
                }
            }
            dcs.add(currentDc);
        } catch (Exception e) {
            log.error("Failed to get all DCs", e);
            dcs.add(currentDc);
        }
        return dcs;
    }

    private DcQuota getDcQuotaFromRedis(String dc) {
        try {
            String quotaKey = RateLimitConstants.REDIS_CLUSTER_DC_QUOTA_KEY + ":" + dc;
            String json = stringRedisTemplate.opsForValue().get(quotaKey);
            if (json != null) {
                return JSON.parseObject(json, DcQuota.class);
            }
        } catch (Exception e) {
            log.error("Failed to get DC quota from Redis for: {}", dc, e);
        }
        return null;
    }

    public Set<String> getClusterClients() {
        String clientKey = RateLimitConstants.REDIS_CLUSTER_DC_KEY + ":" + currentDc + ":clients";
        Set<String> clients = stringRedisTemplate.opsForSet().members(clientKey);
        return clients != null ? clients : new HashSet<>();
    }

    public String getClusterServer() {
        String serverKey = RateLimitConstants.REDIS_CLUSTER_DC_KEY + ":" + currentDc + ":server";
        return stringRedisTemplate.opsForValue().get(serverKey);
    }

    public int getCurrentClusterMode() {
        return ClusterStateManager.getState();
    }

    public void switchToClientMode(String serverHost, int serverPort) {
        ClusterStateManager.applyState(ClusterStateManager.CLUSTER_CLIENT);
        ClusterClientConfigManager.applyNewConfig(
                new ClusterClientConfig()
                        .setServerHost(serverHost)
                        .setServerPort(serverPort)
                        .setRequestTimeout(500)
        );
        log.info("Switched to cluster client mode, server: {}:{}", serverHost, serverPort);
    }

    public void switchToServerMode() {
        ClusterStateManager.applyState(ClusterStateManager.CLUSTER_SERVER);
        log.info("Switched to cluster server mode");
    }

    public void recordTokenRequest(String resource, int tokenCount) {
        clientTokenMap.merge(resource, tokenCount, Integer::sum);
    }

    public Map<String, Integer> getTokenStats() {
        return new ConcurrentHashMap<>(clientTokenMap);
    }

    public Map<String, Object> getClusterState() {
        Map<String, Object> state = new HashMap<>();
        state.put("dc", currentDc);
        state.put("nodeId", nodeId);
        state.put("mode", ClusterStateManager.getState());
        state.put("modeName", getModeName(ClusterStateManager.getState()));
        state.put("server", getClusterServer());
        state.put("clients", getClusterClients());
        state.put("totalQuota", totalQuota);
        state.put("localUsage", localUsageMap.entrySet().stream()
                .collect(HashMap::new, (m, e) -> m.put(e.getKey(), e.getValue().get()), HashMap::putAll));
        state.put("tokenStats", getTokenStats());
        state.put("currentDcQuota", getCurrentDcQuota());
        state.put("borrowedQuota", borrowedQuotaMap.entrySet().stream()
                .collect(HashMap::new, (m, e) -> m.put(e.getKey(), e.getValue().get()), HashMap::putAll));
        return state;
    }

    private String getModeName(int mode) {
        switch (mode) {
            case -1: return "NOT_STARTED";
            case 0: return "CLUSTER_OFF";
            case 1: return "CLUSTER_CLIENT";
            case 2: return "CLUSTER_SERVER";
            default: return "UNKNOWN";
        }
    }
}
