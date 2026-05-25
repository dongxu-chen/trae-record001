package com.taskscheduler.core.registry;

import com.taskscheduler.common.entity.ExecutorInfo;
import com.taskscheduler.common.util.JsonUtils;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.apache.curator.framework.CuratorFramework;
import org.apache.curator.framework.CuratorFrameworkFactory;
import org.apache.curator.retry.ExponentialBackoffRetry;
import org.apache.zookeeper.CreateMode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.InetAddress;
import java.time.LocalDateTime;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class ExecutorRegister {

    private static final String ZK_ROOT_PATH = "/task-scheduler";
    private static final String ZK_EXECUTORS_PATH = ZK_ROOT_PATH + "/executors";

    @Value("${task-scheduler.zookeeper.address:127.0.0.1:2181}")
    private String zkAddress;

    @Value("${task-scheduler.executor.name:executor}")
    private String executorName;

    @Value("${task-scheduler.executor.app-name:default-executor}")
    private String appName;

    @Value("${task-scheduler.executor.port:9999}")
    private int executorPort;

    @Value("${task-scheduler.executor.description:}")
    private String description;

    private CuratorFramework client;

    private String executorPath;

    private final ScheduledExecutorService heartbeatExecutor = Executors.newSingleThreadScheduledExecutor();

    @PostConstruct
    public void init() throws Exception {
        client = CuratorFrameworkFactory.newClient(zkAddress,
                new ExponentialBackoffRetry(1000, 3));
        client.start();

        String ip = InetAddress.getLocalHost().getHostAddress();
        String address = ip + ":" + executorPort;
        executorPath = ZK_EXECUTORS_PATH + "/" + address;

        register(address);

        startHeartbeat(address);

        log.info("Executor registered to zookeeper: {}, path: {}", zkAddress, executorPath);
    }

    @PreDestroy
    public void destroy() throws Exception {
        heartbeatExecutor.shutdown();
        if (client != null && executorPath != null) {
            try {
                client.delete().forPath(executorPath);
            } catch (Exception e) {
                log.warn("Delete executor path failed: {}", executorPath, e);
            }
            client.close();
        }
        log.info("Executor unregistered from zookeeper");
    }

    private void register(String address) throws Exception {
        if (client.checkExists().forPath(ZK_ROOT_PATH) == null) {
            client.create().creatingParentsIfNeeded().forPath(ZK_ROOT_PATH);
        }
        if (client.checkExists().forPath(ZK_EXECUTORS_PATH) == null) {
            client.create().creatingParentsIfNeeded().forPath(ZK_EXECUTORS_PATH);
        }

        ExecutorInfo executorInfo = new ExecutorInfo();
        executorInfo.setExecutorName(executorName);
        executorInfo.setExecutorAddress(address);
        executorInfo.setAppName(appName);
        executorInfo.setDescription(description);
        executorInfo.setRegisterTime(LocalDateTime.now());
        executorInfo.setHeartbeatTime(LocalDateTime.now());

        byte[] data = JsonUtils.toJsonString(executorInfo).getBytes();

        if (client.checkExists().forPath(executorPath) != null) {
            client.setData().forPath(executorPath, data);
        } else {
            client.create()
                    .creatingParentsIfNeeded()
                    .withMode(CreateMode.EPHEMERAL)
                    .forPath(executorPath, data);
        }
    }

    private void startHeartbeat(String address) {
        heartbeatExecutor.scheduleAtFixedRate(() -> {
            try {
                ExecutorInfo executorInfo = new ExecutorInfo();
                executorInfo.setExecutorName(executorName);
                executorInfo.setExecutorAddress(address);
                executorInfo.setAppName(appName);
                executorInfo.setDescription(description);
                executorInfo.setHeartbeatTime(LocalDateTime.now());

                byte[] data = JsonUtils.toJsonString(executorInfo).getBytes();
                if (client.checkExists().forPath(executorPath) != null) {
                    client.setData().forPath(executorPath, data);
                } else {
                    register(address);
                }
            } catch (Exception e) {
                log.error("Heartbeat update failed", e);
                try {
                    register(address);
                } catch (Exception ex) {
                    log.error("Re-register executor failed", ex);
                }
            }
        }, 30, 30, TimeUnit.SECONDS);
    }
}
