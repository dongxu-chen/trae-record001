package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MonitoringDashboard {
    private String dashboardId;
    private Date generatedAt;
    private MigrationOverview migrationOverview;
    private ServiceHealthSummary serviceHealth;
    private RegistrySyncStatus registrySyncStatus;
    private TrafficDistribution trafficDistribution;
    @Builder.Default
    private List<RecentAlert> recentAlerts = new ArrayList<>();
    @Builder.Default
    private List<MigrationProgress> migrationProgressList = new ArrayList<>();
    private PerformanceMetricsSnapshot performanceMetrics;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MigrationOverview {
        private int totalServices;
        private int migratedServices;
        private int inProgressServices;
        private int pendingServices;
        private int failedServices;
        private double overallProgress;
        private String estimatedRemainingTime;
        private Date startTime;
        private String currentPhase;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ServiceHealthSummary {
        private int totalServicesEureka;
        private int totalServicesNacos;
        private int healthyServicesEureka;
        private int healthyServicesNacos;
        private int unhealthyServicesEureka;
        private int unhealthyServicesNacos;
        private double eurekaHealthRate;
        private double nacosHealthRate;
        @Builder.Default
        private List<ServiceHealthDetail> unhealthyServices = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ServiceHealthDetail {
        private String serviceId;
        private String registry;
        private String status;
        private int instanceCount;
        private int healthyInstances;
        private int unhealthyInstances;
        private Date lastCheckTime;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RegistrySyncStatus {
        private boolean syncRunning;
        private String syncMode;
        private String syncDirection;
        private int syncedServiceCount;
        private int pendingSyncCount;
        private int failedSyncCount;
        private Date lastSyncTime;
        private long syncIntervalMs;
        private long lastSyncDurationMs;
        private double syncSuccessRate;
        @Builder.Default
        private List<String> recentSyncErrors = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TrafficDistribution {
        private double overallNacosRatio;
        private double overallEurekaRatio;
        private int servicesFullNacos;
        private int servicesFullEureka;
        private int servicesGrayscale;
        @Builder.Default
        private List<TrafficDetail> serviceTrafficDetails = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TrafficDetail {
        private String serviceId;
        private double nacosRatio;
        private int nacosPercentage;
        private String status;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RecentAlert {
        private String alertId;
        private AlertLevel level;
        private String type;
        private String message;
        private String serviceId;
        private Date timestamp;
        private boolean acknowledged;

        public enum AlertLevel {
            INFO,
            WARNING,
            ERROR,
            CRITICAL
        }
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MigrationProgress {
        private String serviceId;
        private String taskId;
        private String phase;
        private String status;
        private int progress;
        private Date startTime;
        private Date endTime;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PerformanceMetricsSnapshot {
        private long eurekaAvgResponseTimeMs;
        private long nacosAvgResponseTimeMs;
        private long eurekaP99ResponseTimeMs;
        private long nacosP99ResponseTimeMs;
        private int eurekaRequestCount;
        private int nacosRequestCount;
        private double eurekaErrorRate;
        private double nacosErrorRate;
        private Date timestamp;
    }
}
