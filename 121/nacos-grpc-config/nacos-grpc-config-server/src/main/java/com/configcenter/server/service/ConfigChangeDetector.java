package com.configcenter.server.service;

import com.configcenter.protocol.ConfigChangeType;
import com.configcenter.protocol.ConfigItem;
import com.configcenter.server.model.ConfigSnapshot;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class ConfigChangeDetector {

    private final Map<String, ConfigSnapshot> snapshotCache = new ConcurrentHashMap<>();

    public List<ConfigItem> detectChanges(String dataId, String group, String namespace, 
                                          Map<String, String> newConfigs) {
        String cacheKey = buildCacheKey(dataId, group, namespace);
        ConfigSnapshot oldSnapshot = snapshotCache.get(cacheKey);
        
        if (oldSnapshot == null) {
            // 首次检测，所有配置视为新增
            List<ConfigItem> changes = new ArrayList<>();
            for (Map.Entry<String, String> entry : newConfigs.entrySet()) {
                changes.add(buildConfigItem(entry.getKey(), entry.getValue(), ConfigChangeType.ADDED));
            }
            
            // 缓存快照
            cacheSnapshot(dataId, group, namespace, newConfigs);
            return changes;
        }

        // 检测变更
        Map<String, String> oldConfigs = oldSnapshot.getParsedConfigs();
        List<ConfigItem> changes = new ArrayList<>();

        // 检测新增和修改
        for (Map.Entry<String, String> entry : newConfigs.entrySet()) {
            String key = entry.getKey();
            String newValue = entry.getValue();
            String oldValue = oldConfigs.get(key);
            
            if (oldValue == null) {
                changes.add(buildConfigItem(key, newValue, ConfigChangeType.ADDED));
            } else if (!Objects.equals(oldValue, newValue)) {
                changes.add(buildConfigItem(key, newValue, ConfigChangeType.MODIFIED));
            }
        }

        // 检测删除
        for (String oldKey : oldConfigs.keySet()) {
            if (!newConfigs.containsKey(oldKey)) {
                changes.add(buildConfigItem(oldKey, null, ConfigChangeType.DELETED));
            }
        }

        // 更新缓存
        if (!changes.isEmpty()) {
            cacheSnapshot(dataId, group, namespace, newConfigs);
            log.info("配置变更检测完成, dataId: {}, 变更数量: {}", dataId, changes.size());
        }

        return changes;
    }

    private ConfigItem buildConfigItem(String key, String value, ConfigChangeType type) {
        return ConfigItem.newBuilder()
                .setKey(key)
                .setValue(value != null ? value : "")
                .setChangeType(type)
                .setVersion(System.currentTimeMillis())
                .build();
    }

    private void cacheSnapshot(String dataId, String group, String namespace, 
                               Map<String, String> configs) {
        String cacheKey = buildCacheKey(dataId, group, namespace);
        ConfigSnapshot snapshot = ConfigSnapshot.builder()
                .dataId(dataId)
                .group(group)
                .namespace(namespace)
                .parsedConfigs(new HashMap<>(configs))
                .version(System.currentTimeMillis())
                .timestamp(System.currentTimeMillis())
                .md5(calculateMd5(configs.toString()))
                .build();
        snapshotCache.put(cacheKey, snapshot);
    }

    private String buildCacheKey(String dataId, String group, String namespace) {
        return namespace + ":" + group + ":" + dataId;
    }

    private String calculateMd5(String content) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(content.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            return String.valueOf(content.hashCode());
        }
    }

    public long getCurrentVersion(String dataId, String group, String namespace) {
        String cacheKey = buildCacheKey(dataId, group, namespace);
        ConfigSnapshot snapshot = snapshotCache.get(cacheKey);
        return snapshot != null ? snapshot.getVersion() : 0;
    }

    public Map<String, String> getCurrentConfig(String dataId, String group, String namespace) {
        String cacheKey = buildCacheKey(dataId, group, namespace);
        ConfigSnapshot snapshot = snapshotCache.get(cacheKey);
        return snapshot != null ? new HashMap<>(snapshot.getParsedConfigs()) : new HashMap<>();
    }

    public void removeSnapshot(String dataId, String group, String namespace) {
        String cacheKey = buildCacheKey(dataId, group, namespace);
        snapshotCache.remove(cacheKey);
    }
}
