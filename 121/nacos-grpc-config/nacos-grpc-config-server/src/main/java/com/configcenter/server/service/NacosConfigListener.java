package com.configcenter.server.service;

import com.alibaba.nacos.api.NacosFactory;
import com.alibaba.nacos.api.config.ConfigService;
import com.alibaba.nacos.api.config.listener.Listener;
import com.alibaba.nacos.api.exception.NacosException;
import com.configcenter.protocol.ConfigItem;
import com.configcenter.protocol.SubscribeResponse;
import com.configcenter.server.model.ClientSession;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.*;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

@Slf4j
@Service
public class NacosConfigListener {

    @Value("${spring.cloud.nacos.config.server-addr:localhost:8848}")
    private String serverAddr;

    @Value("${spring.cloud.nacos.config.namespace:public}")
    private String namespace;

    @Value("${spring.cloud.nacos.config.group:DEFAULT_GROUP}")
    private String defaultGroup;

    @Autowired
    private ConfigChangeDetector configChangeDetector;

    @Autowired
    private ClientSessionManager clientSessionManager;

    private ConfigService configService;

    private final Map<String, Set<String>> watchedConfigs = new HashMap<>();

    private final Executor executor = Executors.newCachedThreadPool();

    @PostConstruct
    public void init() {
        try {
            Properties properties = new Properties();
            properties.put("serverAddr", serverAddr);
            properties.put("namespace", namespace);
            configService = NacosFactory.createConfigService(properties);
            log.info("Nacos配置服务初始化成功, serverAddr: {}, namespace: {}", serverAddr, namespace);
        } catch (NacosException e) {
            log.error("Nacos配置服务初始化失败", e);
            throw new RuntimeException("Nacos配置服务初始化失败", e);
        }
    }

    public void addConfigListener(String dataId, String group) {
        String key = dataId + ":" + group;
        if (watchedConfigs.containsKey(key)) {
            return;
        }

        try {
            configService.addListener(dataId, group, new Listener() {
                @Override
                public Executor getExecutor() {
                    return executor;
                }

                @Override
                public void receiveConfigInfo(String configInfo) {
                    handleConfigChange(dataId, group, configInfo);
                }
            });

            watchedConfigs.computeIfAbsent(key, k -> new HashSet<>()).add(dataId);
            log.info("已添加Nacos配置监听器, dataId: {}, group: {}", dataId, group);

            // 首次拉取配置并进行快照
            String config = configService.getConfig(dataId, group, 5000);
            if (config != null) {
                Map<String, String> configMap = parseConfig(config);
                configChangeDetector.detectChanges(dataId, group, namespace, configMap);
            }
        } catch (NacosException e) {
            log.error("添加Nacos配置监听器失败, dataId: {}, group: {}", dataId, group, e);
        }
    }

    public void removeConfigListener(String dataId, String group) {
        try {
            configService.removeListener(dataId, group, null);
            String key = dataId + ":" + group;
            watchedConfigs.remove(key);
            configChangeDetector.removeSnapshot(dataId, group, namespace);
            log.info("已移除Nacos配置监听器, dataId: {}, group: {}", dataId, group);
        } catch (NacosException e) {
            log.error("移除Nacos配置监听器失败, dataId: {}, group: {}", dataId, group, e);
        }
    }

    private void handleConfigChange(String dataId, String group, String newConfig) {
        log.info("收到Nacos配置变更, dataId: {}, group: {}", dataId, group);

        try {
            Map<String, String> configMap = parseConfig(newConfig);
            List<ConfigItem> changes = configChangeDetector.detectChanges(dataId, group, namespace, configMap);

            if (!changes.isEmpty()) {
                long version = configChangeDetector.getCurrentVersion(dataId, group, namespace);
                pushChangesToClients(dataId, group, changes, version);
                log.info("配置变更已推送, dataId: {}, 变更项数: {}", dataId, changes.size());
            }
        } catch (Exception e) {
            log.error("处理配置变更失败, dataId: {}, group: {}", dataId, group, e);
        }
    }

    private void pushChangesToClients(String dataId, String group, List<ConfigItem> changes, long version) {
        for (ClientSession session : clientSessionManager.getAllSessions().values()) {
            if (!session.getSubscribedDataIds().contains(dataId)) {
                continue;
            }

            // 检查客户端已知版本，避免重复推送相同版本
            String versionKey = dataId + ":" + group;
            Long knownVersion = session.getKnownVersions().get(versionKey);
            if (knownVersion != null && knownVersion >= version) {
                continue;
            }

            // 推送变更
            pushToClient(session, dataId, group, changes, version);
            session.getKnownVersions().put(versionKey, version);
        }
    }

    private void pushToClient(ClientSession session, String dataId, String group,
                               List<ConfigItem> changes, long version) {
        if (session.getResponseObserver() == null) {
            return;
        }

        try {
            SubscribeResponse response = SubscribeResponse.newBuilder()
                    .setRequestId(generateRequestId())
                    .setDataId(dataId)
                    .setGroup(group)
                    .addAllChangedItems(changes)
                    .setVersion(version)
                    .setStatus(com.configcenter.protocol.ResponseStatus.SUCCESS)
                    .setTimestamp(System.currentTimeMillis())
                    .build();

            session.getResponseObserver().onNext(response);
            log.debug("配置变更已推送到客户端, clientId: {}, dataId: {}, 变更数: {}",
                    session.getClientId(), dataId, changes.size());
        } catch (Exception e) {
            log.error("推送配置变更失败, clientId: {}, dataId: {}", session.getClientId(), dataId, e);
            clientSessionManager.unregisterSession(session.getClientId());
        }
    }

    private Map<String, String> parseConfig(String configContent) {
        Map<String, String> configMap = new HashMap<>();
        if (configContent == null || configContent.trim().isEmpty()) {
            return configMap;
        }

        // 简单的 properties 格式解析
        String[] lines = configContent.split("\n");
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#") || line.startsWith("!")) {
                continue;
            }
            int equalsIndex = line.indexOf('=');
            if (equalsIndex > 0) {
                String key = line.substring(0, equalsIndex).trim();
                String value = line.substring(equalsIndex + 1).trim();
                configMap.put(key, value);
            }
        }

        return configMap;
    }

    public String getConfig(String dataId, String group, long timeoutMs) {
        try {
            return configService.getConfig(dataId, group, timeoutMs);
        } catch (NacosException e) {
            log.error("获取Nacos配置失败, dataId: {}, group: {}", dataId, group, e);
            return null;
        }
    }

    public Map<String, String> getConfigMap(String dataId, String group) {
        String config = getConfig(dataId, group, 5000);
        return parseConfig(config);
    }

    private String generateRequestId() {
        return "REQ-" + System.currentTimeMillis() + "-" + (int)(Math.random() * 1000);
    }

    @PreDestroy
    public void destroy() {
        log.info("关闭Nacos配置监听器，共 {} 个监听配置", watchedConfigs.size());
        for (String key : watchedConfigs.keySet()) {
            String[] parts = key.split(":");
            if (parts.length == 2) {
                removeConfigListener(parts[0], parts[1]);
            }
        }
        watchedConfigs.clear();
    }
}
