package com.migration.engine;

import com.migration.client.EurekaClient;
import com.migration.model.MigrationPlan;
import com.migration.model.MigrationPlan.MigrationBatch;
import com.migration.model.MigrationPlan.PlanStatus;
import com.migration.model.MigrationPlan.PlanStrategy;
import com.migration.model.MigrationPlan.HealthCheckResult;
import com.migration.model.ServiceInstance;
import com.migration.verify.ConsistencyVerifier;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class MigrationPlanEngine {

    private final EurekaClient eurekaClient;
    private final MigrationEngine migrationEngine;
    private final RegistrySyncEngine registrySyncEngine;
    private final ConsistencyVerifier consistencyVerifier;
    private final Map<String, MigrationPlan> plans = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
    private final Map<String, Boolean> runningPlans = new ConcurrentHashMap<>();

    public MigrationPlanEngine(EurekaClient eurekaClient,
                               MigrationEngine migrationEngine,
                               RegistrySyncEngine registrySyncEngine,
                               ConsistencyVerifier consistencyVerifier) {
        this.eurekaClient = eurekaClient;
        this.migrationEngine = migrationEngine;
        this.registrySyncEngine = registrySyncEngine;
        this.consistencyVerifier = consistencyVerifier;
    }

    public MigrationPlan createPlan(String planName, String description, int batchSize, PlanStrategy strategy) {
        String planId = UUID.randomUUID().toString();
        MigrationPlan plan = MigrationPlan.builder()
                .planId(planId)
                .planName(planName)
                .description(description)
                .strategy(strategy)
                .batchSize(batchSize)
                .batchIntervalMs(30000L)
                .autoContinue(true)
                .healthCheckBeforeNext(true)
                .successThreshold(0.95)
                .status(PlanStatus.DRAFT)
                .createdAt(new Date())
                .build();
        plans.put(planId, plan);
        log.info("Created migration plan: {} [{}]", planName, planId);
        return plan;
    }

    public MigrationPlan configureBatchServices(String planId, List<String> serviceIds, int batchSize) {
        MigrationPlan plan = plans.get(planId);
        if (plan == null) {
            throw new IllegalArgumentException("Plan not found: " + planId);
        }

        List<List<String>> batches = partitionServices(serviceIds, batchSize);
        List<MigrationBatch> migrationBatches = new ArrayList<>();

        for (int i = 0; i < batches.size(); i++) {
            migrationBatches.add(MigrationBatch.builder()
                    .batchNumber(i + 1)
                    .batchName("Batch " + (i + 1))
                    .serviceIds(batches.get(i))
                    .status(MigrationBatch.BatchStatus.PENDING)
                    .build());
        }

        plan.setBatches(migrationBatches);
        plan.setTotalBatches(migrationBatches.size());
        plan.setCurrentBatch(0);
        plan.setBatchSize(batchSize);

        log.info("Configured plan {} with {} batches for {} services",
                planId, migrationBatches.size(), serviceIds.size());
        return plan;
    }

    public MigrationPlan autoConfigurePlan(String planId, int batchSize, List<String> priorityServices,
                                           List<String> excludeServices) {
        List<String> allServices = eurekaClient.getAllServiceIds();
        List<String> servicesToMigrate = new ArrayList<>();

        if (priorityServices != null) {
            servicesToMigrate.addAll(priorityServices);
        }

        for (String service : allServices) {
            if (!servicesToMigrate.contains(service)
                    && (excludeServices == null || !excludeServices.contains(service))) {
                servicesToMigrate.add(service);
            }
        }

        return configureBatchServices(planId, servicesToMigrate, batchSize);
    }

    public MigrationPlan startPlan(String planId) {
        MigrationPlan plan = plans.get(planId);
        if (plan == null) {
            throw new IllegalArgumentException("Plan not found: " + planId);
        }

        if (plan.getBatches().isEmpty()) {
            throw new IllegalStateException("Plan has no batches configured");
        }

        plan.setStatus(PlanStatus.RUNNING);
        plan.setStartTime(new Date());
        plan.setCurrentBatch(0);

        runningPlans.put(planId, true);
        scheduleNextBatch(planId);

        log.info("Started migration plan: {}", planId);
        return plan;
    }

    public MigrationPlan pausePlan(String planId) {
        MigrationPlan plan = plans.get(planId);
        if (plan == null) {
            throw new IllegalArgumentException("Plan not found: " + planId);
        }

        plan.setStatus(PlanStatus.PAUSED);
        runningPlans.remove(planId);

        log.info("Paused migration plan: {}", planId);
        return plan;
    }

    public MigrationPlan resumePlan(String planId) {
        MigrationPlan plan = plans.get(planId);
        if (plan == null) {
            throw new IllegalArgumentException("Plan not found: " + planId);
        }

        plan.setStatus(PlanStatus.RUNNING);
        runningPlans.put(planId, true);

        scheduleNextBatch(planId);

        log.info("Resumed migration plan: {}", planId);
        return plan;
    }

    public MigrationPlan cancelPlan(String planId) {
        MigrationPlan plan = plans.get(planId);
        if (plan == null) {
            throw new IllegalArgumentException("Plan not found: " + planId);
        }

        plan.setStatus(PlanStatus.CANCELLED);
        runningPlans.remove(planId);

        log.info("Cancelled migration plan: {}", planId);
        return plan;
    }

    private void scheduleNextBatch(String planId) {
        scheduler.schedule(() -> executeNextBatch(planId), 0, TimeUnit.MILLISECONDS);
    }

    private void executeNextBatch(String planId) {
        MigrationPlan plan = plans.get(planId);
        if (plan == null || !runningPlans.getOrDefault(planId, false)) {
            return;
        }

        int nextBatchIndex = plan.getCurrentBatch();
        if (nextBatchIndex >= plan.getBatches().size()) {
            completePlan(planId);
            return;
        }

        MigrationBatch batch = plan.getBatches().get(nextBatchIndex);
        batch.setStatus(MigrationBatch.BatchStatus.RUNNING);
        batch.setStartTime(new Date());

        log.info("Executing batch {} of plan {}: {} services",
                nextBatchIndex + 1, planId, batch.getServiceIds().size());

        for (String serviceId : batch.getServiceIds()) {
            try {
                migrationEngine.startServiceMigration(serviceId);
                batch.getSuccessfulServices().add(serviceId);
                log.info("Migrated service: {}", serviceId);
            } catch (Exception e) {
                batch.getFailedServices().add(serviceId);
                log.error("Failed to migrate service: {}", serviceId, e);
            }
        }

        if (batch.getFailedServices().isEmpty()) {
            batch.setStatus(MigrationBatch.BatchStatus.COMPLETED);
        } else if (batch.getSuccessfulServices().isEmpty()) {
            batch.setStatus(MigrationBatch.BatchStatus.FAILED);
        } else {
            batch.setStatus(MigrationBatch.BatchStatus.PARTIALLY_SUCCESSFUL);
        }
        batch.setCompletedTime(new Date());

        if (plan.isHealthCheckBeforeNext()) {
            HealthCheckResult healthResult = performHealthCheck(batch);
            batch.setHealthCheckResult(healthResult);

            if (!healthResult.isPassed() && healthResult.getSuccessRate() < plan.getSuccessThreshold()) {
                plan.setStatus(PlanStatus.PAUSED);
                runningPlans.remove(planId);
                log.warn("Health check failed for batch {} of plan {}, pausing plan",
                        nextBatchIndex + 1, planId);
                return;
            }
        }

        plan.setCurrentBatch(nextBatchIndex + 1);

        if (plan.isAutoContinue() && runningPlans.getOrDefault(planId, false)) {
            scheduler.schedule(() -> executeNextBatch(planId), plan.getBatchIntervalMs(), TimeUnit.MILLISECONDS);
        }
    }

    private HealthCheckResult performHealthCheck(MigrationBatch batch) {
        int total = batch.getServiceIds().size();
        int healthy = 0;
        List<String> unhealthy = new ArrayList<>();

        for (String serviceId : batch.getServiceIds()) {
            try {
                List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
                boolean healthyService = !eurekaInstances.isEmpty() &&
                        eurekaInstances.stream().allMatch(i -> "UP".equals(i.getStatus()));
                if (healthyService) {
                    healthy++;
                } else {
                    unhealthy.add(serviceId);
                }
            } catch (Exception e) {
                unhealthy.add(serviceId);
            }
        }

        double successRate = total > 0 ? (double) healthy / total : 0;

        return HealthCheckResult.builder()
                .passed(successRate >= 0.8)
                .successRate(successRate)
                .totalServices(total)
                .healthyServices(healthy)
                .unhealthyServices(unhealthy.size())
                .unhealthyServiceIds(unhealthy)
                .summary(String.format("Health check: %d/%d healthy (%.1f%%)",
                        healthy, total, successRate * 100))
                .checkedAt(new Date())
                .build();
    }

    private void completePlan(String planId) {
        MigrationPlan plan = plans.get(planId);
        if (plan == null) {
            return;
        }

        long failedBatches = plan.getBatches().stream()
                .filter(b -> b.getStatus() == MigrationBatch.BatchStatus.FAILED)
                .count();

        plan.setStatus(failedBatches > 0 ? PlanStatus.FAILED : PlanStatus.COMPLETED);
        plan.setCompletedTime(new Date());
        runningPlans.remove(planId);

        log.info("Completed migration plan: {} with {} failed batches", planId, failedBatches);
    }

    private List<List<String>> partitionServices(List<String> services, int batchSize) {
        List<List<String>> batches = new ArrayList<>();
        for (int i = 0; i < services.size(); i += batchSize) {
            int end = Math.min(i + batchSize, services.size());
            batches.add(new ArrayList<>(services.subList(i, end)));
        }
        return batches;
    }

    public MigrationPlan getPlan(String planId) {
        return plans.get(planId);
    }

    public List<MigrationPlan> getAllPlans() {
        return new ArrayList<>(plans.values());
    }

    public void deletePlan(String planId) {
        plans.remove(planId);
        runningPlans.remove(planId);
    }
}
