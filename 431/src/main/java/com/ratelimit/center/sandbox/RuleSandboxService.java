package com.ratelimit.center.sandbox;

import com.alibaba.csp.sentinel.Entry;
import com.alibaba.csp.sentinel.EntryType;
import com.alibaba.csp.sentinel.SphU;
import com.alibaba.csp.sentinel.context.ContextUtil;
import com.alibaba.csp.sentinel.slots.block.BlockException;
import com.alibaba.csp.sentinel.slots.block.RuleConstant;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRule;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRuleManager;
import com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowRule;
import com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowRuleManager;
import com.alibaba.fastjson.JSON;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.entity.FlowRuleEntity;
import com.ratelimit.center.entity.ParamFlowRuleEntity;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Service
public class RuleSandboxService {

    private final Map<String, SandboxTask> runningTasks = new ConcurrentHashMap<>();
    private final Map<String, List<FlowRule>> originalFlowRules = new ConcurrentHashMap<>();
    private final Map<String, List<ParamFlowRule>> originalParamRules = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(5);

    @Data
    public static class SandboxRequest {
        private String resourceName;
        private int qps = 100;
        private int durationSeconds = 30;
        private int concurrency = 10;
        private String ruleType = "flow";
        private FlowRuleEntity flowRule;
        private ParamFlowRuleEntity paramFlowRule;
        private List<Object> paramValues;
        private String warmUpType = "none";
        private int warmUpSeconds = 0;
    }

    @Data
    public static class SandboxResult {
        private String taskId;
        private String resourceName;
        private int totalRequests;
        private int passedRequests;
        private int blockedRequests;
        private double actualQps;
        private double passRate;
        private double blockRate;
        private double avgRt;
        private List<TimePoint> timeSeries;
        private String status;
        private String ruleConfig;
        private String errorMessage;
        private long startTime;
        private long endTime;
    }

    @Data
    public static class TimePoint {
        private long timestamp;
        private int requests;
        private int passed;
        private int blocked;
        private double avgRt;
    }

    @Data
    public static class SandboxTask {
        private String taskId;
        private SandboxRequest request;
        private SandboxResult result;
        private Future<?> future;
        private volatile boolean running;
        private AtomicInteger totalCount = new AtomicInteger(0);
        private AtomicInteger passCount = new AtomicInteger(0);
        private AtomicInteger blockCount = new AtomicInteger(0);
        private AtomicLong totalRt = new AtomicLong(0);
        private List<TimePoint> timePoints = Collections.synchronizedList(new ArrayList<>());
    }

    public String startSandbox(SandboxRequest request) {
        String taskId = UUID.randomUUID().toString().replace("-", "");
        SandboxTask task = new SandboxTask();
        task.setTaskId(taskId);
        task.setRequest(request);
        task.setRunning(true);

        saveOriginalRules(request.getResourceName());

        applyTestRules(request);

        SandboxResult result = new SandboxResult();
        result.setTaskId(taskId);
        result.setResourceName(request.getResourceName());
        result.setStartTime(System.currentTimeMillis());
        result.setStatus("running");
        task.setResult(result);

        runningTasks.put(taskId, task);

        Future<?> future = scheduler.submit(() -> runSandbox(task));
        task.setFuture(future);

        scheduler.schedule(() -> stopSandbox(taskId), request.getDurationSeconds(), TimeUnit.SECONDS);

        return taskId;
    }

    private void runSandbox(SandboxTask task) {
        SandboxRequest request = task.getRequest();
        String resourceName = request.getResourceName();

        long intervalMs = 1000;
        long requestsPerInterval = request.getQps();
        ExecutorService executor = Executors.newFixedThreadPool(request.getConcurrency());

        while (task.isRunning() && !Thread.currentThread().isInterrupted()) {
            long intervalStart = System.currentTimeMillis();

            CountDownLatch latch = new CountDownLatch((int) requestsPerInterval);
            AtomicInteger intervalPass = new AtomicInteger(0);
            AtomicInteger intervalBlock = new AtomicInteger(0);
            AtomicLong intervalRt = new AtomicLong(0);

            for (int i = 0; i < requestsPerInterval; i++) {
                final int idx = i;
                executor.submit(() -> {
                    if (!task.isRunning()) {
                        latch.countDown();
                        return;
                    }

                    long startTime = System.nanoTime();
                    Entry entry = null;
                    try {
                        ContextUtil.enter(resourceName, "sandbox");

                        if (RateLimitConstants.RULE_TYPE_PARAM_FLOW.equals(request.getRuleType())
                                && request.getParamValues() != null && !request.getParamValues().isEmpty()) {
                            Object param = request.getParamValues().get(idx % request.getParamValues().size());
                            entry = SphU.entry(resourceName, EntryType.IN, 1, param);
                        } else {
                            entry = SphU.entry(resourceName, EntryType.IN);
                        }

                        task.getPassCount().incrementAndGet();
                        intervalPass.incrementAndGet();
                    } catch (BlockException e) {
                        task.getBlockCount().incrementAndGet();
                        intervalBlock.incrementAndGet();
                    } catch (Exception e) {
                        log.warn("Sandbox request error", e);
                    } finally {
                        if (entry != null) {
                            entry.exit();
                        }
                        ContextUtil.exit();

                        long rt = (System.nanoTime() - startTime) / 1000000;
                        task.getTotalRt().addAndGet(rt);
                        intervalRt.addAndGet(rt);

                        task.getTotalCount().incrementAndGet();
                        latch.countDown();
                    }
                });
            }

            try {
                latch.await(intervalMs, TimeUnit.MILLISECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }

            TimePoint point = new TimePoint();
            point.setTimestamp(System.currentTimeMillis());
            point.setRequests((int) requestsPerInterval);
            point.setPassed(intervalPass.get());
            point.setBlocked(intervalBlock.get());
            int totalInterval = intervalPass.get() + intervalBlock.get();
            if (totalInterval > 0) {
                point.setAvgRt(intervalRt.get() / (double) totalInterval);
            } else {
                point.setAvgRt(0);
            }
            task.getTimePoints().add(point);

            long elapsed = System.currentTimeMillis() - intervalStart;
            long sleepTime = intervalMs - elapsed;
            if (sleepTime > 0 && task.isRunning()) {
                try {
                    Thread.sleep(sleepTime);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }

        executor.shutdownNow();
        finishTask(task);
    }

    private void finishTask(SandboxTask task) {
        task.setRunning(false);
        SandboxResult result = task.getResult();
        SandboxRequest request = task.getRequest();

        result.setTotalRequests(task.getTotalCount().get());
        result.setPassedRequests(task.getPassCount().get());
        result.setBlockedRequests(task.getBlockCount().get());
        result.setEndTime(System.currentTimeMillis());

        long durationMs = result.getEndTime() - result.getStartTime();
        if (durationMs > 0) {
            result.setActualQps(task.getTotalCount().get() * 1000.0 / durationMs);
        }

        if (task.getTotalCount().get() > 0) {
            result.setPassRate(task.getPassCount().get() * 100.0 / task.getTotalCount().get());
            result.setBlockRate(task.getBlockCount().get() * 100.0 / task.getTotalCount().get());
            result.setAvgRt(task.getTotalRt().get() / (double) task.getTotalCount().get());
        }

        result.setTimeSeries(new ArrayList<>(task.getTimePoints()));
        result.setRuleConfig(JSON.toJSONString(request));
        result.setStatus("completed");

        restoreOriginalRules(request.getResourceName());
    }

    public SandboxResult getSandboxResult(String taskId) {
        SandboxTask task = runningTasks.get(taskId);
        if (task == null) {
            return null;
        }

        SandboxResult result = task.getResult();
        if ("running".equals(result.getStatus())) {
            result.setTotalRequests(task.getTotalCount().get());
            result.setPassedRequests(task.getPassCount().get());
            result.setBlockedRequests(task.getBlockCount().get());
            result.setTimeSeries(new ArrayList<>(task.getTimePoints()));

            long durationMs = System.currentTimeMillis() - result.getStartTime();
            if (durationMs > 0) {
                result.setActualQps(task.getTotalCount().get() * 1000.0 / durationMs);
            }
            if (task.getTotalCount().get() > 0) {
                result.setPassRate(task.getPassCount().get() * 100.0 / task.getTotalCount().get());
                result.setBlockRate(task.getBlockCount().get() * 100.0 / task.getTotalCount().get());
                result.setAvgRt(task.getTotalRt().get() / (double) task.getTotalCount().get());
            }
        }

        return result;
    }

    public void stopSandbox(String taskId) {
        SandboxTask task = runningTasks.get(taskId);
        if (task != null && task.isRunning()) {
            task.setRunning(false);
            if (task.getFuture() != null) {
                task.getFuture().cancel(true);
            }
            finishTask(task);
        }
    }

    public List<SandboxResult> listSandboxTasks() {
        List<SandboxResult> results = new ArrayList<>();
        for (SandboxTask task : runningTasks.values()) {
            results.add(getSandboxResult(task.getTaskId()));
        }
        return results;
    }

    private void saveOriginalRules(String resourceName) {
        List<FlowRule> flowRules = FlowRuleManager.getRules();
        List<FlowRule> resourceFlowRules = new ArrayList<>();
        for (FlowRule rule : flowRules) {
            if (resourceName.equals(rule.getResource())) {
                resourceFlowRules.add(rule);
            }
        }
        originalFlowRules.put(resourceName, resourceFlowRules);

        List<ParamFlowRule> paramRules = ParamFlowRuleManager.getRules();
        List<ParamFlowRule> resourceParamRules = new ArrayList<>();
        for (ParamFlowRule rule : paramRules) {
            if (resourceName.equals(rule.getResource())) {
                resourceParamRules.add(rule);
            }
        }
        originalParamRules.put(resourceName, resourceParamRules);
    }

    private void applyTestRules(SandboxRequest request) {
        String resourceName = request.getResourceName();

        if (RateLimitConstants.RULE_TYPE_FLOW.equals(request.getRuleType()) && request.getFlowRule() != null) {
            FlowRuleEntity entity = request.getFlowRule();
            FlowRule rule = new FlowRule();
            rule.setResource(resourceName);
            rule.setGrade(entity.getGrade() != null ? entity.getGrade() : RuleConstant.FLOW_GRADE_QPS);
            rule.setCount(entity.getCount() != null ? entity.getCount() : 100);
            rule.setLimitApp(entity.getLimitApp() != null ? entity.getLimitApp() : "default");
            rule.setStrategy(entity.getStrategy() != null ? entity.getStrategy() : RuleConstant.STRATEGY_DIRECT);
            rule.setControlBehavior(entity.getControlBehavior() != null ? entity.getControlBehavior() : RuleConstant.CONTROL_BEHAVIOR_DEFAULT);
            if (entity.getWarmUpPeriodSec() != null && entity.getWarmUpPeriodSec() > 0) {
                rule.setWarmUpPeriodSec(entity.getWarmUpPeriodSec());
                rule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_WARM_UP);
            }
            if (entity.getMaxQueueingTimeMs() != null && entity.getMaxQueueingTimeMs() > 0) {
                rule.setMaxQueueingTimeMs(entity.getMaxQueueingTimeMs());
                rule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_RATE_LIMITER);
            }

            List<FlowRule> rules = new ArrayList<>();
            rules.add(rule);
            FlowRuleManager.loadRules(rules);

            log.info("Sandbox applied flow rule: {}", JSON.toJSONString(rule));
        } else if (RateLimitConstants.RULE_TYPE_PARAM_FLOW.equals(request.getRuleType()) && request.getParamFlowRule() != null) {
            ParamFlowRuleEntity entity = request.getParamFlowRule();
            ParamFlowRule rule = new ParamFlowRule();
            rule.setResource(resourceName);
            rule.setGrade(entity.getGrade() != null ? entity.getGrade() : RuleConstant.FLOW_GRADE_QPS);
            rule.setCount(entity.getCount() != null ? entity.getCount() : 100);
            rule.setParamIdx(entity.getParamIdx() != null ? entity.getParamIdx() : 0);
            if (entity.getParamFlowItemList() != null && !entity.getParamFlowItemList().isEmpty()) {
                rule.setParamFlowItemList(entity.getParamFlowItemList());
            }

            List<ParamFlowRule> rules = new ArrayList<>();
            rules.add(rule);
            ParamFlowRuleManager.loadRules(rules);

            log.info("Sandbox applied param flow rule: {}", JSON.toJSONString(rule));
        }
    }

    private void restoreOriginalRules(String resourceName) {
        List<FlowRule> originalFlow = originalFlowRules.get(resourceName);
        if (originalFlow != null) {
            List<FlowRule> allRules = new ArrayList<>(FlowRuleManager.getRules());
            allRules.removeIf(r -> resourceName.equals(r.getResource()));
            allRules.addAll(originalFlow);
            FlowRuleManager.loadRules(allRules);
        }

        List<ParamFlowRule> originalParam = originalParamRules.get(resourceName);
        if (originalParam != null) {
            List<ParamFlowRule> allRules = new ArrayList<>(ParamFlowRuleManager.getRules());
            allRules.removeIf(r -> resourceName.equals(r.getResource()));
            allRules.addAll(originalParam);
            ParamFlowRuleManager.loadRules(allRules);
        }

        originalFlowRules.remove(resourceName);
        originalParamRules.remove(resourceName);

        log.info("Sandbox restored original rules for: {}", resourceName);
    }

    public SandboxResult quickTest(FlowRuleEntity flowRule, int testQps, int durationSeconds) {
        SandboxRequest request = new SandboxRequest();
        request.setResourceName(flowRule.getResource());
        request.setRuleType(RateLimitConstants.RULE_TYPE_FLOW);
        request.setFlowRule(flowRule);
        request.setQps(testQps);
        request.setDurationSeconds(durationSeconds);
        request.setConcurrency(10);

        String taskId = startSandbox(request);

        try {
            Thread.sleep(durationSeconds * 1000L + 500);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        return getSandboxResult(taskId);
    }
}
