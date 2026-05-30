package com.distid.snowflake;

import lombok.extern.slf4j.Slf4j;
import org.apache.zookeeper.CreateMode;
import org.apache.zookeeper.KeeperException;
import org.apache.curator.framework.CuratorFramework;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.nio.charset.StandardCharsets;

@Slf4j
public class ConsistentHashWorkerIdAssigner {

    private static final String NAMESPACE = "/distid-snowflake";
    private static final String WORKERS_PATH = NAMESPACE + "/workers";
    private static final long MAX_WORKER_ID = 31L;

    private final CuratorFramework curator;
    private final String podName;
    private volatile long assignedWorkerId = -1;
    private volatile String ephemeralNodePath;
    private volatile boolean running = true;

    public ConsistentHashWorkerIdAssigner(CuratorFramework curator, String podName) {
        this.curator = curator;
        this.podName = podName != null && !podName.isEmpty() ? podName : getDefaultPodName();
    }

    private String getDefaultPodName() {
        String hostname = System.getenv("HOSTNAME");
        if (hostname != null && !hostname.isEmpty()) {
            return hostname;
        }
        try {
            return java.net.InetAddress.getLocalHost().getHostName();
        } catch (Exception e) {
            return "pod-" + System.currentTimeMillis();
        }
    }

    @PostConstruct
    public void init() throws Exception {
        long candidateId = murmur3Hash(podName) & 0xFFFFFFFFL;
        candidateId = candidateId % (MAX_WORKER_ID + 1);

        assignedWorkerId = tryAssignWorkerId(candidateId);

        if (assignedWorkerId == -1) {
            assignedWorkerId = findAvailableWorkerId();
        }

        if (assignedWorkerId == -1) {
            throw new IllegalStateException("No available workerId slot, all 32 slots occupied");
        }

        log.info("Assigned workerId={} for podName={}, hash-based candidateId={}",
                assignedWorkerId, podName, candidateId);

        startHeartbeat();
    }

    private long tryAssignWorkerId(long workerId) throws Exception {
        ensurePathExists(WORKERS_PATH);
        String path = WORKERS_PATH + "/" + workerId;
        try {
            ephemeralNodePath = curator.create()
                    .creatingParentsIfNeeded()
                    .withMode(CreateMode.EPHEMERAL)
                    .forPath(path, podName.getBytes(StandardCharsets.UTF_8));
            return workerId;
        } catch (KeeperException.NodeExistsException e) {
            String existingOwner = getNodeOwner(path);
            log.warn("workerId={} already occupied by pod={}, candidate pod={}",
                    workerId, existingOwner, podName);
            return -1;
        }
    }

    private String getNodeOwner(String path) {
        try {
            byte[] data = curator.getData().forPath(path);
            return new String(data, StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "unknown";
        }
    }

    private long findAvailableWorkerId() throws Exception {
        for (long id = 0; id <= MAX_WORKER_ID; id++) {
            if (id == assignedWorkerId) continue;
            String path = WORKERS_PATH + "/" + id;
            try {
                ephemeralNodePath = curator.create()
                        .creatingParentsIfNeeded()
                        .withMode(CreateMode.EPHEMERAL)
                        .forPath(path, podName.getBytes(StandardCharsets.UTF_8));
                return id;
            } catch (KeeperException.NodeExistsException ignored) {
            }
        }
        return -1;
    }

    private void ensurePathExists(String path) throws Exception {
        try {
            if (curator.checkExists().forPath(path) == null) {
                curator.create().creatingParentsIfNeeded().forPath(path);
            }
        } catch (KeeperException.NodeExistsException ignored) {
        }
    }

    private void startHeartbeat() {
        Thread heartbeatThread = new Thread(() -> {
            while (running) {
                try {
                    Thread.sleep(5000);
                    if (ephemeralNodePath != null && curator.checkExists().forPath(ephemeralNodePath) == null) {
                        log.warn("Ephemeral node lost for workerId={}, attempting to re-register", assignedWorkerId);
                        tryRecover();
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.error("Heartbeat check failed", e);
                }
            }
        }, "workerid-heartbeat-" + podName);
        heartbeatThread.setDaemon(true);
        heartbeatThread.start();
    }

    private void tryRecover() {
        try {
            String recovered = curator.create()
                    .withMode(CreateMode.EPHEMERAL)
                    .forPath(WORKERS_PATH + "/" + assignedWorkerId, podName.getBytes(StandardCharsets.UTF_8));
            this.ephemeralNodePath = recovered;
            log.info("Recovered ephemeral node at path={}", recovered);
        } catch (KeeperException.NodeExistsException e) {
            log.error("Cannot recover workerId={}, slot already taken. Will shutdown.", assignedWorkerId);
            running = false;
        } catch (Exception e) {
            log.error("Failed to recover workerId", e);
            running = false;
        }
    }

    @PreDestroy
    public void release() {
        running = false;
        try {
            if (ephemeralNodePath != null) {
                curator.delete().forPath(ephemeralNodePath);
                log.info("Released workerId={}, deleted ephemeral node={}", assignedWorkerId, ephemeralNodePath);
            }
        } catch (Exception e) {
            log.warn("Failed to delete ephemeral node on shutdown", e);
        }
    }

    public long getAssignedWorkerId() {
        return assignedWorkerId;
    }

    public String getPodName() {
        return podName;
    }

    public boolean isRunning() {
        return running;
    }

    public static int murmur3Hash(String key) {
        byte[] bytes = key.getBytes(StandardCharsets.UTF_8);
        return murmur3Hash32(bytes, 0, bytes.length, 0x9747b28c);
    }

    private static int murmur3Hash32(byte[] data, int offset, int length, int seed) {
        final int c1 = 0xcc9e2d51;
        final int c2 = 0x1b873593;

        int h1 = seed;
        int roundedEnd = offset + (length & 0xfffffffc);

        for (int i = offset; i < roundedEnd; i += 4) {
            int k1 = (data[i] & 0xff) | ((data[i + 1] & 0xff) << 8)
                    | ((data[i + 2] & 0xff) << 16) | (data[i + 3] << 24);
            k1 *= c1;
            k1 = Integer.rotateLeft(k1, 15);
            k1 *= c2;
            h1 ^= k1;
            h1 = Integer.rotateLeft(h1, 13);
            h1 = h1 * 5 + 0xe6546b64;
        }

        int k1 = 0;
        switch (length & 3) {
            case 3:
                k1 ^= (data[roundedEnd + 2] & 0xff) << 16;
            case 2:
                k1 ^= (data[roundedEnd + 1] & 0xff) << 8;
            case 1:
                k1 ^= (data[roundedEnd] & 0xff);
                k1 *= c1;
                k1 = Integer.rotateLeft(k1, 15);
                k1 *= c2;
                h1 ^= k1;
        }

        h1 ^= length;
        h1 ^= h1 >>> 16;
        h1 *= 0x85ebca6b;
        h1 ^= h1 >>> 13;
        h1 *= 0xc2b2ae35;
        h1 ^= h1 >>> 16;

        return h1;
    }
}
