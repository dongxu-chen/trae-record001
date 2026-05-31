package com.drill.platform.service;

import com.drill.platform.engine.TrafficSimulator;
import com.drill.platform.jmeter.JMeterRunner;
import com.drill.platform.model.*;
import com.drill.platform.report.ReportGenerator;
import com.drill.platform.sentinel.SentinelManager;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Slf4j
@Service
public class DrillService {

    private final Map<String, DrillTask> taskStore = new ConcurrentHashMap<>();
    private final Map<String, DrillReport> reportStore = new ConcurrentHashMap<>();
    private final Map<String, RateLimitStrategy> strategyStore = new ConcurrentHashMap<>();
    private final Map<String, TrafficSimulator> runningSimulators = new ConcurrentHashMap<>();
    private final ExecutorService drillExecutor = Executors.newFixedThreadPool(5);

    private final SentinelManager sentinelManager;
    private final JMeterRunner jMeterRunner;
    private final ReportGenerator reportGenerator;

    public DrillService(SentinelManager sentinelManager, JMeterRunner jMeterRunner, ReportGenerator reportGenerator) {
        this.sentinelManager = sentinelManager;
        this.jMeterRunner = jMeterRunner;
        this.reportGenerator = reportGenerator;
    }

    public DrillTask createTask(DrillTask task) {
        if (task.getId() == null) {
            task.setId(UUID.randomUUID().toString());
        }
        task.setStatus(DrillTask.DrillStatus.CREATED);
        task.setCreateTime(new Date());
        if (task.getTrafficProfile() == null) {
            task.setTrafficProfile(TrafficProfile.defaultProfile());
        }
        taskStore.put(task.getId(), task);
        log.info("Created drill task: {}", task.getId());
        return task;
    }

    public DrillTask startTask(String taskId, String mode) {
        DrillTask task = taskStore.get(taskId);
        if (task == null) {
            throw new IllegalArgumentException("Task not found: " + taskId);
        }
        if (task.getStatus() == DrillTask.DrillStatus.RUNNING) {
            throw new IllegalStateException("Task already running: " + taskId);
        }

        RateLimitStrategy strategy = strategyStore.get(task.getStrategyId());
        if (strategy != null && strategy.isEnabled()) {
            sentinelManager.applyStrategy(strategy);
        }

        task.setStatus(DrillTask.DrillStatus.RUNNING);
        task.setStartTime(new Date());

        if ("jmeter".equalsIgnoreCase(mode) && jMeterRunner.isJMeterAvailable()) {
            drillExecutor.submit(() -> {
                try {
                    DrillResult result = jMeterRunner.runTest(task.getTrafficProfile(), task.getId());
                    task.setResult(result);
                    task.setStatus(DrillTask.DrillStatus.COMPLETED);
                    task.setEndTime(new Date());
                    generateReport(task, strategy);
                } catch (Exception e) {
                    log.error("JMeter drill failed for task: {}", taskId, e);
                    task.setStatus(DrillTask.DrillStatus.FAILED);
                    task.setEndTime(new Date());
                }
            });
        } else {
            drillExecutor.submit(() -> {
                try {
                    TrafficSimulator simulator = new TrafficSimulator(
                            task.getTrafficProfile(),
                            profile -> executeSimulatedRequest(profile, strategy)
                    );
                    runningSimulators.put(taskId, simulator);
                    DrillResult result = simulator.simulate();
                    runningSimulators.remove(taskId);

                    task.setResult(result);
                    task.setStatus(DrillTask.DrillStatus.COMPLETED);
                    task.setEndTime(new Date());
                    generateReport(task, strategy);
                } catch (Exception e) {
                    log.error("Simulator drill failed for task: {}", taskId, e);
                    task.setStatus(DrillTask.DrillStatus.FAILED);
                    task.setEndTime(new Date());
                }
            });
        }

        log.info("Started drill task: {} in mode: {}", taskId, mode);
        return task;
    }

    private TrafficSimulator.RequestResult executeSimulatedRequest(TrafficProfile profile, RateLimitStrategy strategy) {
        if (strategy != null) {
            com.drill.platform.sentinel.SentinelResult sentinelResult = sentinelManager.entry(strategy.getId());
            if (sentinelResult.isBlocked()) {
                return TrafficSimulator.RequestResult.blocked(429, sentinelResult.getFallbackResponse());
            }
        }

        try {
            java.net.HttpURLConnection connection = (java.net.HttpURLConnection)
                    new java.net.URL(profile.getTargetUrl()).openConnection();
            connection.setRequestMethod(profile.getHttpMethod());
            connection.setConnectTimeout(profile.getConnectTimeoutMs());
            connection.setReadTimeout(profile.getReadTimeoutMs());

            int responseCode = connection.getResponseCode();

            if (responseCode == 429 || responseCode == 503) {
                sentinelManager.recordDegrade(strategy != null ? strategy.getId() : "default");
                return TrafficSimulator.RequestResult.blocked(responseCode, "Service unavailable");
            }

            if (responseCode >= 500) {
                return TrafficSimulator.RequestResult.failed(new RuntimeException("Server error: " + responseCode));
            }

            if (responseCode >= 200 && responseCode < 300) {
                return TrafficSimulator.RequestResult.success(responseCode, "OK");
            }

            return TrafficSimulator.RequestResult.success(responseCode, "Response received");
        } catch (Exception e) {
            return TrafficSimulator.RequestResult.failed(e);
        }
    }

    public DrillTask stopTask(String taskId) {
        DrillTask task = taskStore.get(taskId);
        if (task == null) {
            throw new IllegalArgumentException("Task not found: " + taskId);
        }

        TrafficSimulator simulator = runningSimulators.get(taskId);
        if (simulator != null) {
            simulator.stop();
        }

        task.setStatus(DrillTask.DrillStatus.CANCELLED);
        task.setEndTime(new Date());
        log.info("Stopped drill task: {}", taskId);
        return task;
    }

    public DrillTask getTask(String taskId) {
        return taskStore.get(taskId);
    }

    public List<DrillTask> listTasks() {
        return new ArrayList<>(taskStore.values());
    }

    public void deleteTask(String taskId) {
        taskStore.remove(taskId);
        reportStore.remove(taskId);
    }

    public RateLimitStrategy createStrategy(RateLimitStrategy strategy) {
        if (strategy.getId() == null) {
            strategy.setId(UUID.randomUUID().toString());
        }
        strategyStore.put(strategy.getId(), strategy);
        log.info("Created strategy: {}", strategy.getId());
        return strategy;
    }

    public RateLimitStrategy updateStrategy(String strategyId, RateLimitStrategy strategy) {
        strategy.setId(strategyId);
        strategyStore.put(strategyId, strategy);
        if (strategy.isEnabled()) {
            sentinelManager.applyStrategy(strategy);
        }
        return strategy;
    }

    public void deleteStrategy(String strategyId) {
        strategyStore.remove(strategyId);
        sentinelManager.removeStrategy(strategyId);
    }

    public RateLimitStrategy getStrategy(String strategyId) {
        return strategyStore.get(strategyId);
    }

    public List<RateLimitStrategy> listStrategies() {
        return new ArrayList<>(strategyStore.values());
    }

    public DrillReport generateReport(DrillTask task, RateLimitStrategy strategy) {
        DrillReport report = reportGenerator.generate(task, strategy != null ? strategy : RateLimitStrategy.defaultStrategy());
        if (report != null) {
            reportStore.put(task.getId(), report);
        }
        return report;
    }

    public DrillReport getReport(String taskId) {
        return reportStore.get(taskId);
    }

    public List<DrillReport> listReports() {
        return new ArrayList<>(reportStore.values());
    }
}
