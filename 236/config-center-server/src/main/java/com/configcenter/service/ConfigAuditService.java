package com.configcenter.service;

import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

@Service
public class ConfigAuditService {

    private final Map<String, ConfigAccessRecord> accessRecords = new ConcurrentHashMap<>();
    private final Map<String, InstanceInfo> activeInstances = new ConcurrentHashMap<>();
    private final Map<String, ConfigUsageStats> usageStats = new ConcurrentHashMap<>();

    public void recordConfigAccess(String application, String profile, String version,
                                   String instanceId, String clientIp, String clientHost) {
        String key = getConfigKey(application, profile, version);

        ConfigAccessRecord record = accessRecords.computeIfAbsent(key, k -> new ConfigAccessRecord(application, profile, version));
        record.recordAccess(instanceId, clientIp, clientHost);

        String instanceKey = getInstanceKey(instanceId, application, profile);
        InstanceInfo instance = activeInstances.computeIfAbsent(instanceKey, k ->
                new InstanceInfo(instanceId, application, profile, clientIp, clientHost));
        instance.setLastAccessTime(LocalDateTime.now());
        instance.setCurrentVersion(version);

        ConfigUsageStats stats = usageStats.computeIfAbsent(key, k -> new ConfigUsageStats(application, profile, version));
        stats.incrementAccessCount();
    }

    public List<ConfigAccessRecord> getAccessRecords(String application, String profile) {
        return accessRecords.values().stream()
                .filter(r -> application == null || r.getApplication().equals(application))
                .filter(r -> profile == null || r.getProfile().equals(profile))
                .sorted((a, b) -> b.getLastAccessTime().compareTo(a.getLastAccessTime()))
                .collect(Collectors.toList());
    }

    public List<InstanceInfo> getActiveInstances(String application, String profile) {
        return activeInstances.values().stream()
                .filter(i -> application == null || i.getApplication().equals(application))
                .filter(i -> profile == null || i.getProfile().equals(profile))
                .sorted((a, b) -> b.getLastAccessTime().compareTo(a.getLastAccessTime()))
                .collect(Collectors.toList());
    }

    public List<ConfigUsageStats> getUsageStats(String application, String profile) {
        return usageStats.values().stream()
                .filter(s -> application == null || s.getApplication().equals(application))
                .filter(s -> profile == null || s.getProfile().equals(profile))
                .sorted((a, b) -> Integer.compare(b.getAccessCount(), a.getAccessCount()))
                .collect(Collectors.toList());
    }

    public Map<String, Object> getConfigAuditSummary(String application, String profile) {
        Map<String, Object> summary = new LinkedHashMap<>();

        List<InstanceInfo> instances = getActiveInstances(application, profile);
        List<ConfigUsageStats> stats = getUsageStats(application, profile);

        summary.put("application", application);
        summary.put("profile", profile);
        summary.put("totalInstances", instances.size());
        summary.put("totalVersions", stats.size());

        Map<String, Integer> versionDistribution = new HashMap<>();
        for (InstanceInfo instance : instances) {
            String version = instance.getCurrentVersion() != null ?
                    instance.getCurrentVersion().substring(0, 8) : "unknown";
            versionDistribution.merge(version, 1, Integer::sum);
        }
        summary.put("versionDistribution", versionDistribution);

        int totalAccesses = stats.stream().mapToInt(ConfigUsageStats::getAccessCount).sum();
        summary.put("totalAccesses", totalAccesses);

        InstanceInfo mostRecent = instances.stream()
                .max(Comparator.comparing(InstanceInfo::getLastAccessTime))
                .orElse(null);
        if (mostRecent != null) {
            summary.put("lastAccessTime", mostRecent.getLastAccessTime());
            summary.put("lastAccessInstance", mostRecent.getInstanceId());
        }

        return summary;
    }

    public Map<String, Object> getInstanceDetail(String instanceId) {
        InstanceInfo instance = activeInstances.values().stream()
                .filter(i -> i.getInstanceId().equals(instanceId))
                .findFirst()
                .orElse(null);

        if (instance == null) {
            return null;
        }

        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("instanceId", instance.getInstanceId());
        detail.put("application", instance.getApplication());
        detail.put("profile", instance.getProfile());
        detail.put("clientIp", instance.getClientIp());
        detail.put("clientHost", instance.getClientHost());
        detail.put("currentVersion", instance.getCurrentVersion());
        detail.put("lastAccessTime", instance.getLastAccessTime());
        detail.put("firstAccessTime", instance.getFirstAccessTime());

        long minutesSinceLastAccess = java.time.Duration.between(
                instance.getLastAccessTime(), LocalDateTime.now()).toMinutes();
        detail.put("minutesSinceLastAccess", minutesSinceLastAccess);
        detail.put("isActive", minutesSinceLastAccess < 30);

        return detail;
    }

    public void cleanupOldRecords(int maxAgeMinutes) {
        LocalDateTime cutoff = LocalDateTime.now().minusMinutes(maxAgeMinutes);

        activeInstances.entrySet().removeIf(entry ->
                entry.getValue().getLastAccessTime().isBefore(cutoff));
    }

    private String getConfigKey(String application, String profile, String version) {
        return application + "/" + profile + "/" + version;
    }

    private String getInstanceKey(String instanceId, String application, String profile) {
        return instanceId + "/" + application + "/" + profile;
    }

    public static class ConfigAccessRecord {
        private final String application;
        private final String profile;
        private final String version;
        private LocalDateTime lastAccessTime;
        private final Set<String> accessingInstances;
        private final Set<String> accessingIps;

        public ConfigAccessRecord(String application, String profile, String version) {
            this.application = application;
            this.profile = profile;
            this.version = version;
            this.accessingInstances = ConcurrentHashMap.newKeySet();
            this.accessingIps = ConcurrentHashMap.newKeySet();
        }

        public synchronized void recordAccess(String instanceId, String clientIp, String clientHost) {
            this.lastAccessTime = LocalDateTime.now();
            this.accessingInstances.add(instanceId);
            this.accessingIps.add(clientIp);
        }

        public String getApplication() { return application; }
        public String getProfile() { return profile; }
        public String getVersion() { return version; }
        public LocalDateTime getLastAccessTime() { return lastAccessTime; }
        public Set<String> getAccessingInstances() { return accessingInstances; }
        public Set<String> getAccessingIps() { return accessingIps; }
        public int getInstanceCount() { return accessingInstances.size(); }
    }

    public static class InstanceInfo {
        private final String instanceId;
        private final String application;
        private final String profile;
        private final String clientIp;
        private final String clientHost;
        private String currentVersion;
        private LocalDateTime lastAccessTime;
        private final LocalDateTime firstAccessTime;

        public InstanceInfo(String instanceId, String application, String profile,
                            String clientIp, String clientHost) {
            this.instanceId = instanceId;
            this.application = application;
            this.profile = profile;
            this.clientIp = clientIp;
            this.clientHost = clientHost;
            this.firstAccessTime = LocalDateTime.now();
            this.lastAccessTime = LocalDateTime.now();
        }

        public String getInstanceId() { return instanceId; }
        public String getApplication() { return application; }
        public String getProfile() { return profile; }
        public String getClientIp() { return clientIp; }
        public String getClientHost() { return clientHost; }
        public String getCurrentVersion() { return currentVersion; }
        public void setCurrentVersion(String currentVersion) { this.currentVersion = currentVersion; }
        public LocalDateTime getLastAccessTime() { return lastAccessTime; }
        public void setLastAccessTime(LocalDateTime lastAccessTime) { this.lastAccessTime = lastAccessTime; }
        public LocalDateTime getFirstAccessTime() { return firstAccessTime; }
    }

    public static class ConfigUsageStats {
        private final String application;
        private final String profile;
        private final String version;
        private final AtomicInteger accessCount;
        private final AtomicInteger uniqueInstances;

        public ConfigUsageStats(String application, String profile, String version) {
            this.application = application;
            this.profile = profile;
            this.version = version;
            this.accessCount = new AtomicInteger(0);
            this.uniqueInstances = new AtomicInteger(0);
        }

        public void incrementAccessCount() {
            accessCount.incrementAndGet();
        }

        public String getApplication() { return application; }
        public String getProfile() { return profile; }
        public String getVersion() { return version; }
        public int getAccessCount() { return accessCount.get(); }
        public int getUniqueInstances() { return uniqueInstances.get(); }
    }
}
