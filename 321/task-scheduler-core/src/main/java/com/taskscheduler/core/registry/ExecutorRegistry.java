package com.taskscheduler.core.registry;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import com.taskscheduler.common.dto.Result;
import com.taskscheduler.common.entity.ExecutorInfo;
import com.taskscheduler.common.enums.ExecutorStatusEnum;
import com.taskscheduler.common.util.JsonUtils;
import com.taskscheduler.core.mapper.ExecutorInfoMapper;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.apache.curator.framework.CuratorFramework;
import org.apache.curator.framework.CuratorFrameworkFactory;
import org.apache.curator.framework.recipes.cache.ChildData;
import org.apache.curator.framework.recipes.cache.PathChildrenCache;
import org.apache.curator.framework.recipes.cache.PathChildrenCacheEvent;
import org.apache.curator.framework.recipes.cache.PathChildrenCacheListener;
import org.apache.curator.retry.ExponentialBackoffRetry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class ExecutorRegistry {

    private static final String ZK_ROOT_PATH = "/task-scheduler";
    private static final String ZK_EXECUTORS_PATH = ZK_ROOT_PATH + "/executors";
    private static final int MAX_HEARTBEAT_FAILURES = 3;
    private static final int HEARTBEAT_TIMEOUT = 5000;

    @Value("${task-scheduler.zookeeper.address:127.0.0.1:2181}")
    private String zkAddress;

    @Autowired
    private ExecutorInfoMapper executorInfoMapper;

    private CuratorFramework client;

    private final ConcurrentHashMap<String, ExecutorInfo> executorCache = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Integer> heartbeatFailureCount = new ConcurrentHashMap<>();

    private PathChildrenCache pathChildrenCache;

    @PostConstruct
    public void init() throws Exception {
        client = CuratorFrameworkFactory.newClient(zkAddress,
                new ExponentialBackoffRetry(1000, 3));
        client.start();

        if (client.checkExists().forPath(ZK_ROOT_PATH) == null) {
            client.create().creatingParentsIfNeeded().forPath(ZK_ROOT_PATH);
        }
        if (client.checkExists().forPath(ZK_EXECUTORS_PATH) == null) {
            client.create().creatingParentsIfNeeded().forPath(ZK_EXECUTORS_PATH);
        }

        pathChildrenCache = new PathChildrenCache(client, ZK_EXECUTORS_PATH, true);
        pathChildrenCache.getListenable().addListener(new ExecutorNodeListener());
        pathChildrenCache.start();

        loadExistingExecutors();

        log.info("ExecutorRegistry initialized with zk: {}, max heartbeat failures: {}",
                zkAddress, MAX_HEARTBEAT_FAILURES);
    }

    @PreDestroy
    public void destroy() throws Exception {
        if (pathChildrenCache != null) {
            pathChildrenCache.close();
        }
        if (client != null) {
            client.close();
        }
    }

    @Scheduled(fixedDelay = 10000)
    public void checkExecutorHealth() {
        List<String> addresses = new ArrayList<>(executorCache.keySet());
        if (addresses.isEmpty()) {
            return;
        }

        log.debug("Checking health for {} executors", addresses.size());

        for (String address : addresses) {
            ExecutorInfo executor = executorCache.get(address);
            if (executor == null) {
                continue;
            }

            if (ExecutorStatusEnum.ONLINE.getCode().equals(executor.getStatus())) {
                boolean healthy = sendHeartbeat(executor);
                if (healthy) {
                    handleHeartbeatSuccess(address, executor);
                } else {
                    handleHeartbeatFailure(address, executor);
                }
            }
        }
    }

    private boolean sendHeartbeat(ExecutorInfo executor) {
        String url = "http://" + executor.getExecutorAddress() + "/api/executor/heartbeat";
        try {
            HttpResponse response = HttpRequest.get(url)
                    .timeout(HEARTBEAT_TIMEOUT)
                    .execute();

            if (response.isOk()) {
                String body = response.body();
                Result<?> result = JsonUtils.parseObject(body, Result.class);
                return result != null && result.getCode() != null && result.getCode() == 200;
            }
            log.warn("Heartbeat response not OK for {}, status: {}", executor.getExecutorAddress(), response.getStatus());
            return false;
        } catch (Exception e) {
            log.warn("Heartbeat failed for {}, error: {}", executor.getExecutorAddress(), e.getMessage());
            return false;
        }
    }

    private void handleHeartbeatSuccess(String address, ExecutorInfo executor) {
        heartbeatFailureCount.remove(address);
        executor.setHeartbeatTime(LocalDateTime.now());
        executor.setUpdateTime(LocalDateTime.now());
        executorInfoMapper.updateById(executor);
        executorCache.put(address, executor);
    }

    private void handleHeartbeatFailure(String address, ExecutorInfo executor) {
        int failures = heartbeatFailureCount.getOrDefault(address, 0) + 1;
        heartbeatFailureCount.put(address, failures);

        log.warn("Heartbeat failure {}/{} for executor: {}",
                failures, MAX_HEARTBEAT_FAILURES, address);

        if (failures >= MAX_HEARTBEAT_FAILURES) {
            log.error("Heartbeat failed {} times consecutively, unregistering executor: {}",
                    MAX_HEARTBEAT_FAILURES, address);
            unregisterExecutor(address);
            heartbeatFailureCount.remove(address);
        }
    }

    private void loadExistingExecutors() throws Exception {
        List<String> children = client.getChildren().forPath(ZK_EXECUTORS_PATH);
        for (String child : children) {
            String path = ZK_EXECUTORS_PATH + "/" + child;
            try {
                byte[] data = client.getData().forPath(path);
                if (data != null && data.length > 0) {
                    ExecutorInfo executor = JsonUtils.parseObject(new String(data), ExecutorInfo.class);
                    if (executor != null) {
                        registerExecutor(executor);
                    }
                }
            } catch (Exception e) {
                log.error("Load executor failed, path: {}", path, e);
            }
        }
    }

    public List<ExecutorInfo> getAvailableExecutors() {
        List<ExecutorInfo> result = new ArrayList<>();
        for (ExecutorInfo executor : executorCache.values()) {
            if (executor.getStatus() != null && executor.getStatus().equals(ExecutorStatusEnum.ONLINE.getCode())) {
                result.add(executor);
            }
        }
        return result;
    }

    public List<ExecutorInfo> getAllExecutors() {
        return new ArrayList<>(executorCache.values());
    }

    private void registerExecutor(ExecutorInfo executor) {
        executor.setStatus(ExecutorStatusEnum.ONLINE.getCode());
        executor.setHeartbeatTime(LocalDateTime.now());

        ExecutorInfo exist = executorInfoMapper.selectOne(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<ExecutorInfo>()
                        .eq("executor_address", executor.getExecutorAddress())
        );

        if (exist == null) {
            executor.setRegisterTime(LocalDateTime.now());
            executor.setCreateTime(LocalDateTime.now());
            executor.setUpdateTime(LocalDateTime.now());
            executorInfoMapper.insert(executor);
        } else {
            executor.setId(exist.getId());
            executor.setUpdateTime(LocalDateTime.now());
            executorInfoMapper.updateById(executor);
        }

        executorCache.put(executor.getExecutorAddress(), executor);
        heartbeatFailureCount.remove(executor.getExecutorAddress());
        log.info("Executor registered: {}, failure count reset", executor.getExecutorAddress());
    }

    private void unregisterExecutor(String address) {
        ExecutorInfo executor = executorCache.get(address);
        if (executor != null) {
            executor.setStatus(ExecutorStatusEnum.OFFLINE.getCode());
            executor.setUpdateTime(LocalDateTime.now());
            executorInfoMapper.updateById(executor);
            executorCache.remove(address);
            heartbeatFailureCount.remove(address);
            log.info("Executor unregistered: {}", address);
        }
    }

    private class ExecutorNodeListener implements PathChildrenCacheListener {
        @Override
        public void childEvent(CuratorFramework client, PathChildrenCacheEvent event) throws Exception {
            ChildData data = event.getData();
            if (data == null) {
                return;
            }

            String path = data.getPath();
            String address = path.substring(ZK_EXECUTORS_PATH.length() + 1);

            switch (event.getType()) {
                case CHILD_ADDED:
                case CHILD_UPDATED:
                    byte[] nodeData = data.getData();
                    if (nodeData != null && nodeData.length > 0) {
                        ExecutorInfo executor = JsonUtils.parseObject(new String(nodeData), ExecutorInfo.class);
                        if (executor != null) {
                            registerExecutor(executor);
                        }
                    }
                    break;
                case CHILD_REMOVED:
                    unregisterExecutor(address);
                    break;
                default:
                    break;
            }
        }
    }

    public int getHeartbeatFailureCount(String address) {
        return heartbeatFailureCount.getOrDefault(address, 0);
    }

    public void refreshExecutorStatus() {
        LocalDateTime timeoutThreshold = LocalDateTime.now().minusMinutes(3);
        for (ExecutorInfo executor : executorCache.values()) {
            if (executor.getHeartbeatTime() != null && executor.getHeartbeatTime().isBefore(timeoutThreshold)) {
                log.warn("Executor heartbeat timeout (3min), unregistering: {}", executor.getExecutorAddress());
                unregisterExecutor(executor.getExecutorAddress());
            }
        }
    }
}
