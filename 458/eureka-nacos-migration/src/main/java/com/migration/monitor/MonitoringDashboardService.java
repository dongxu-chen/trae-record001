package com.migration.monitor;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.engine.MigrationEngine;
import com.migration.engine.MigrationPlanEngine;
import com.migration.engine.RegistrySyncEngine;
import com.migration.engine.SwitchRehearsalEngine;
import com.migration.model.*;
import com.migration.model.MonitoringDashboard.*;
import com.migration.model.MonitoringDashboard.RecentAlert.AlertLevel;
import com.migration.traffic.TrafficRouter;
import com.migration.verify.ConsistencyVerifier;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentLinkedQueue;

@Slf4j
@Component
public class MonitoringDashboardService {

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;
    private final MigrationEngine migrationEngine;
    private final MigrationPlanEngine migrationPlanEngine;
    private final RegistrySyncEngine registrySyncEngine;
    private final TrafficRouter trafficRouter;
    private final ConsistencyVerifier consistencyVerifier;
    private final SwitchRehearsalEngine rehearsalEngine;
    private final Queue<RecentAlert> alertQueue = new ConcurrentLinkedQueue<>();
    private static final int MAX_ALERTS = 100;

    public MonitoringDashboardService(EurekaClient eurekaClient,
                                      NacosClient nacosClient,
                                      MigrationEngine migrationEngine,
                                      MigrationPlanEngine migrationPlanEngine,
                                      RegistrySyncEngine registrySyncEngine,
                                      TrafficRouter trafficRouter,
                                      ConsistencyVerifier consistencyVerifier,
                                      SwitchRehearsalEngine rehearsalEngine) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
        this.migrationEngine = migrationEngine;
        this.migrationPlanEngine = migrationPlanEngine;
        this.registrySyncEngine = registrySyncEngine;
        this.trafficRouter = trafficRouter;
        this.consistencyVerifier = consistencyVerifier;
        this.rehearsalEngine = rehearsalEngine;
    }

    public MonitoringDashboard generateDashboard() {
        return MonitoringDashboard.builder()
                .dashboardId(UUID.randomUUID().toString())
                .generatedAt(new Date())
                .migrationOverview(generateMigrationOverview())
                .serviceHealth(generateServiceHealth())
                .registrySyncStatus(generateRegistrySyncStatus())
                .trafficDistribution(generateTrafficDistribution())
                .recentAlerts(getRecentAlerts())
                .migrationProgressList(generateMigrationProgressList())
                .performanceMetrics(generatePerformanceSnapshot())
                .build();
    }

    private MigrationOverview generateMigrationOverview() {
        List<String> eurekaServices = eurekaClient.getAllServiceIds();
        List<String> nacosServices = nacosClient.getAllServiceIds();

        Set<String> allServices = new HashSet<>();
        allServices.addAll(eurekaServices);
        allServices.addAll(nacosServices);

        int totalServices = allServices.size();
        int migratedServices = (int) nacosServices.stream()
                .filter(eurekaServices::contains)
                .count();
        int inProgressServices = 0;
        int pendingServices = eurekaServices.size() - migratedServices;
        int failedServices = 0;

        List<MigrationTask> tasks = migrationEngine.getAllTasks();
        for (MigrationTask task : tasks) {
            if (task.getStatus() == MigrationTask.TaskStatus.IN_PROGRESS) {
                inProgressServices++;
            } else if (task.getStatus() == MigrationTask.TaskStatus.FAILED) {
                failedServices++;
            }
        }

        double progress = totalServices > 0
                ? (migratedServices * 100.0 / totalServices)
                : 0;

        return MigrationOverview.builder()
                .totalServices(totalServices)
                .migratedServices(migratedServices)
                .inProgressServices(inProgressServices)
                .pendingServices(pendingServices)
                .failedServices(failedServices)
                .overallProgress(progress)
                .estimatedRemainingTime(calculateEstimatedTime(pendingServices))
                .startTime(tasks.isEmpty() ? null : tasks.get(0).getStartTime())
                .currentPhase(determineCurrentPhase(migratedServices, totalServices))
                .build();
    }

    private String calculateEstimatedTime(int pendingServices) {
        if (pendingServices <= 0) return "已完成";
        long avgTimePerService = 30;
        long totalSeconds = pendingServices * avgTimePerService;

        if (totalSeconds < 60) return totalSeconds + " 秒";
        if (totalSeconds < 3600) return (totalSeconds / 60) + " 分钟";
        return (totalSeconds / 3600) + " 小时 " + ((totalSeconds % 3600) / 60) + " 分钟";
    }

    private String determineCurrentPhase(int migrated, int total) {
        if (total == 0) return "未开始";
        double ratio = (double) migrated / total;
        if (ratio == 0) return "准备阶段";
        if (ratio < 0.1) return "服务同步中";
        if (ratio < 0.5) return "灰度迁移中";
        if (ratio < 1.0) return "批量迁移中";
        return "迁移完成";
    }

    private ServiceHealthSummary generateServiceHealth() {
        List<String> eurekaServices = eurekaClient.getAllServiceIds();
        List<String> nacosServices = nacosClient.getAllServiceIds();

        List<ServiceHealthDetail> unhealthyServices = new ArrayList<>();

        int healthyEureka = 0;
        int unhealthyEureka = 0;
        for (String serviceId : eurekaServices) {
            List<ServiceInstance> instances = eurekaClient.getInstances(serviceId);
            int healthyCount = (int) instances.stream()
                    .filter(i -> "UP".equals(i.getStatus()))
                    .count();
            if (healthyCount == instances.size()) {
                healthyEureka++;
            } else {
                unhealthyEureka++;
                unhealthyServices.add(ServiceHealthDetail.builder()
                        .serviceId(serviceId)
                        .registry("EUREKA")
                        .status(unhealthyCount > 0 ? "DEGRADED" : "HEALTHY")
                        .instanceCount(instances.size())
                        .healthyInstances(healthyCount)
                        .unhealthyInstances(instances.size() - healthyCount)
                        .lastCheckTime(new Date())
                        .build());
            }
        }

        int healthyNacos = 0;
        int unhealthyNacos = 0;
        for (String serviceId : nacosServices) {
            List<ServiceInstance> instances = nacosClient.getInstances(serviceId);
            int healthyCount = (int) instances.stream()
                    .filter(i -> "UP".equals(i.getStatus()))
                    .count();
            if (healthyCount == instances.size()) {
                healthyNacos++;
            } else {
                unhealthyNacos++;
                unhealthyServices.add(ServiceHealthDetail.builder()
                        .serviceId(serviceId)
                        .registry("NACOS")
                        .status(unhealthyCount > 0 ? "DEGRADED" : "HEALTHY")
                        .instanceCount(instances.size())
                        .healthyInstances(healthyCount)
                        .unhealthyInstances(instances.size() - healthyCount)
                        .lastCheckTime(new Date())
                        .build());
            }
        }

        return ServiceHealthSummary.builder()
                .totalServicesEureka(eurekaServices.size())
                .totalServicesNacos(nacosServices.size())
                .healthyServicesEureka(healthyEureka)
                .healthyServicesNacos(healthyNacos)
                .unhealthyServicesEureka(unhealthyEureka)
                .unhealthyServicesNacos(unhealthyNacos)
                .eurekaHealthRate(eurekaServices.size() > 0 ? (double) healthyEureka / eurekaServices.size() : 0)
                .nacosHealthRate(nacosServices.size() > 0 ? (double) healthyNacos / nacosServices.size() : 0)
                .unhealthyServices(unhealthyServices)
                .build();
    }

    private RegistrySyncStatus generateRegistrySyncStatus() {
        List<RegistrySyncEngine.SyncRecord> history = registrySyncEngine.getSyncHistory();
        long lastSyncDuration = 0;
        String lastSyncTime = null;

        if (!history.isEmpty()) {
            RegistrySyncEngine.SyncRecord last = history.get(history.size() - 1);
            lastSyncTime = last.getTimestamp();
        }

        int failedCount = (int) history.stream()
                .filter(r -> r.getFailedCount() > 0)
                .count();

        List<String> recentErrors = new ArrayList<>();
        for (RegistrySyncEngine.SyncRecord record : history) {
            if (!record.getFailedInstances().isEmpty()) {
                recentErrors.add("Sync " + record.getSyncId() + ": " +
                        record.getFailedInstances().size() + " failed instances");
            }
        }

        return RegistrySyncStatus.builder()
                .syncRunning(registrySyncEngine.isSyncRunning())
                .syncMode(registrySyncEngine.getSyncMode().name())
                .syncDirection(registrySyncEngine.getSyncDirection().name())
                .syncedServiceCount(registrySyncEngine.getSyncedInstances().size())
                .pendingSyncCount(0)
                .failedSyncCount(failedCount)
                .lastSyncTime(lastSyncTime != null ? new Date(Long.parseLong(lastSyncTime)) : null)
                .syncIntervalMs(30000L)
                .lastSyncDurationMs(lastSyncDuration)
                .syncSuccessRate(history.isEmpty() ? 1.0 : (double) (history.size() - failedCount) / history.size())
                .recentSyncErrors(recentErrors.subList(0, Math.min(5, recentErrors.size())))
                .build();
    }

    private TrafficDistribution generateTrafficDistribution() {
        Map<String, GrayscaleStrategy> allStrategies = trafficRouter.getAllStrategies();

        int fullNacos = 0;
        int fullEureka = 0;
        int grayscale = 0;
        double totalNacosRatio = 0;

        List<TrafficDetail> details = new ArrayList<>();
        for (Map.Entry<String, GrayscaleStrategy> entry : allStrategies.entrySet()) {
            GrayscaleStrategy strategy = entry.getValue();
            double ratio = strategy.getNacosTrafficRatio();
            totalNacosRatio += ratio;

            if (ratio >= 1.0) fullNacos++;
            else if (ratio <= 0) fullEureka++;
            else grayscale++;

            details.add(TrafficDetail.builder()
                    .serviceId(entry.getKey())
                    .nacosRatio(ratio)
                    .nacosPercentage(strategy.getNacosPercentage())
                    .status(strategy.getStatusDescription())
                    .build());
        }

        return TrafficDistribution.builder()
                .overallNacosRatio(allStrategies.isEmpty() ? 0 : totalNacosRatio / allStrategies.size())
                .overallEurekaRatio(allStrategies.isEmpty() ? 1 : 1 - totalNacosRatio / allStrategies.size())
                .servicesFullNacos(fullNacos)
                .servicesFullEureka(fullEureka)
                .servicesGrayscale(grayscale)
                .serviceTrafficDetails(details)
                .build();
    }

    private List<MigrationProgress> generateMigrationProgressList() {
        List<MigrationProgress> progressList = new ArrayList<>();
        List<MigrationTask> tasks = migrationEngine.getAllTasks();

        for (MigrationTask task : tasks) {
            progressList.add(MigrationProgress.builder()
                    .serviceId(task.getServiceId())
                    .taskId(task.getTaskId())
                    .phase(task.getPhase().name())
                    .status(task.getStatus().name())
                    .progress(task.getProgress())
                    .startTime(task.getStartTime())
                    .endTime(task.getEndTime())
                    .build());
        }

        return progressList;
    }

    private PerformanceMetricsSnapshot generatePerformanceSnapshot() {
        long eurekaStart = System.currentTimeMillis();
        eurekaClient.getAllServiceIds();
        long eurekaTime = System.currentTimeMillis() - eurekaStart;

        long nacosStart = System.currentTimeMillis();
        nacosClient.getAllServiceIds();
        long nacosTime = System.currentTimeMillis() - nacosStart;

        return PerformanceMetricsSnapshot.builder()
                .eurekaAvgResponseTimeMs(eurekaTime)
                .nacosAvgResponseTimeMs(nacosTime)
                .eurekaP99ResponseTimeMs(eurekaTime * 2)
                .nacosP99ResponseTimeMs(nacosTime * 2)
                .eurekaRequestCount(1)
                .nacosRequestCount(1)
                .eurekaErrorRate(0)
                .nacosErrorRate(0)
                .timestamp(new Date())
                .build();
    }

    public void addAlert(AlertLevel level, String type, String message, String serviceId) {
        RecentAlert alert = RecentAlert.builder()
                .alertId(UUID.randomUUID().toString())
                .level(level)
                .type(type)
                .message(message)
                .serviceId(serviceId)
                .timestamp(new Date())
                .acknowledged(false)
                .build();

        alertQueue.offer(alert);
        while (alertQueue.size() > MAX_ALERTS) {
            alertQueue.poll();
        }

        if (level == AlertLevel.ERROR || level == AlertLevel.CRITICAL) {
            log.error("[ALERT] {} - {}: {}", level, type, message);
        } else if (level == AlertLevel.WARNING) {
            log.warn("[ALERT] {} - {}: {}", level, type, message);
        }
    }

    public List<RecentAlert> getRecentAlerts() {
        List<RecentAlert> alerts = new ArrayList<>(alertQueue);
        alerts.sort((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()));
        return alerts.subList(0, Math.min(20, alerts.size()));
    }

    public void acknowledgeAlert(String alertId) {
        for (RecentAlert alert : alertQueue) {
            if (alert.getAlertId().equals(alertId)) {
                alert.setAcknowledged(true);
                break;
            }
        }
    }

    public void refreshAlertsFromConsistencyCheck() {
        ConsistencyCheckResult result = consistencyVerifier.quickVerify();
        if (result.getAlerts() != null) {
            for (String alertMsg : result.getAlerts()) {
                addAlert(AlertLevel.WARNING, "CONSISTENCY", alertMsg, null);
            }
        }
    }
}
