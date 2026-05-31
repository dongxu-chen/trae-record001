package com.datacheck.check;

import com.datacheck.config.ThresholdConfig;
import com.datacheck.datasource.DataSourceAdapter;
import com.datacheck.datasource.DataSourceAdapterFactory;
import com.datacheck.messagequeue.MessageQueueService;
import com.datacheck.model.CheckResult;
import com.datacheck.model.CheckTask;
import com.datacheck.model.DataRecord;
import com.datacheck.model.DiffResult;
import com.datacheck.service.WebSocketService;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Component
public class CheckEngine {

    private final DataSourceAdapterFactory adapterFactory;
    private final DataComparator dataComparator;
    private final WebSocketService webSocketService;
    private final MessageQueueService messageQueueService;
    private final HashChecker hashChecker;
    private final StratifiedSampler stratifiedSampler;
    private final ThresholdConfig thresholdConfig;

    private final Map<String, CheckTask> runningTasks = new ConcurrentHashMap<>();
    private final Cache<String, CheckResult> resultCache = Caffeine.newBuilder()
            .expireAfterWrite(1, TimeUnit.HOURS)
            .maximumSize(100)
            .build();
    private final Cache<String, DiffResult> diffCache = Caffeine.newBuilder()
            .expireAfterWrite(2, TimeUnit.HOURS)
            .maximumSize(10000)
            .build();

    @Value("${check.stratified.stratum-count:10}")
    private int defaultStratumCount;

    @Value("${check.stratified.enabled:true}")
    private boolean defaultStratifiedEnabled;

    @Autowired
    public CheckEngine(DataSourceAdapterFactory adapterFactory,
                       DataComparator dataComparator,
                       WebSocketService webSocketService,
                       MessageQueueService messageQueueService,
                       HashChecker hashChecker,
                       StratifiedSampler stratifiedSampler,
                       ThresholdConfig thresholdConfig) {
        this.adapterFactory = adapterFactory;
        this.dataComparator = dataComparator;
        this.webSocketService = webSocketService;
        this.messageQueueService = messageQueueService;
        this.hashChecker = hashChecker;
        this.stratifiedSampler = stratifiedSampler;
        this.thresholdConfig = thresholdConfig;
    }

    @Async("checkTaskExecutor")
    public void executeCheck(CheckTask task) {
        boolean useStratifiedHash = task.getStratifiedHashEnabled() != null ?
                task.getStratifiedHashEnabled() : defaultStratifiedEnabled;

        if (useStratifiedHash) {
            executeStratifiedHashCheck(task);
        } else {
            executeFullCheck(task);
        }
    }

    private void executeFullCheck(CheckTask task) {
        String taskId = task.getId();
        task.setStatus("RUNNING");
        task.setStartedAt(LocalDateTime.now());
        runningTasks.put(taskId, task);

        log.info("Starting full check task: {}, type: {}, table: {}",
                taskId, task.getSourceType(), task.getTableName());

        CheckResult result = CheckResult.builder()
                .taskId(taskId)
                .sourceType(task.getSourceType())
                .tableName(task.getTableName())
                .startTime(LocalDateTime.now())
                .diffs(new ArrayList<>())
                .metrics(new ConcurrentHashMap<>())
                .checkMode("FULL")
                .build();

        try {
            DataSourceAdapter adapter = adapterFactory.getAdapter(task.getSourceType());

            long sourceCount = adapter.getSourceCount(task);
            long targetCount = adapter.getTargetCount(task);
            result.setTotalSourceRecords(sourceCount);
            result.setTotalTargetRecords(targetCount);

            webSocketService.sendTaskProgress(taskId, "INIT",
                    String.format("Source count: %d, Target count: %d", sourceCount, targetCount));

            AtomicLong processed = new AtomicLong(0);
            AtomicLong diffCount = new AtomicLong(0);
            AtomicLong latencyCount = new AtomicLong(0);
            AtomicLong totalLatency = new AtomicLong(0);
            AtomicLong maxLatency = new AtomicLong(0);

            Iterator<DataRecord> sourceIterator = adapter.iterateSource(task);
            Iterator<DataRecord> targetIterator = adapter.iterateTarget(task);

            Map<String, DataRecord> targetBuffer = new HashMap<>();
            int batchSize = thresholdConfig.getEffectiveBatchSize(task);

            while (sourceIterator.hasNext()) {
                DataRecord sourceRecord = sourceIterator.next();
                if (sourceRecord == null || sourceRecord.getKey() == null) {
                    continue;
                }

                DataRecord targetRecord = findTargetRecord(sourceRecord.getKey(),
                        targetIterator, targetBuffer, adapter, task);

                Optional<DiffResult> diffOpt = dataComparator.compare(sourceRecord, targetRecord, task);
                if (diffOpt.isPresent()) {
                    DiffResult diff = diffOpt.get();
                    result.getDiffs().add(diff);
                    diffCount.incrementAndGet();

                    if (diff.getDiffType().name().contains("LATENCY")) {
                        latencyCount.incrementAndGet();
                        totalLatency.addAndGet(diff.getLatencyMs());
                        maxLatency.set(Math.max(maxLatency.get(), diff.getLatencyMs()));
                    }

                    webSocketService.sendDiff(diff);
                    messageQueueService.sendDiffToQueue(diff);
                    diffCache.put(diff.getId(), diff);
                }

                long currentProcessed = processed.incrementAndGet();
                if (currentProcessed % batchSize == 0) {
                    webSocketService.sendTaskProgress(taskId, "PROCESSING",
                            String.format("Processed: %d, Diffs: %d", currentProcessed, diffCount.get()));
                    log.debug("Check task {} progress: processed={}, diffs={}",
                            taskId, currentProcessed, diffCount.get());
                }
            }

            while (targetIterator.hasNext()) {
                DataRecord targetRecord = targetIterator.next();
                if (targetRecord == null || targetRecord.getKey() == null) {
                    continue;
                }
                if (targetBuffer.containsKey(targetRecord.getKey())) {
                    continue;
                }

                Optional<DiffResult> diffOpt = dataComparator.compare(null, targetRecord, task);
                if (diffOpt.isPresent()) {
                    DiffResult diff = diffOpt.get();
                    result.getDiffs().add(diff);
                    diffCount.incrementAndGet();
                    webSocketService.sendDiff(diff);
                    messageQueueService.sendDiffToQueue(diff);
                    diffCache.put(diff.getId(), diff);
                }
                processed.incrementAndGet();
            }

            result.setDiffCount(diffCount.get());
            result.setLatencyCount(latencyCount.get());
            if (latencyCount.get() > 0) {
                result.setAvgLatencyMs((double) totalLatency.get() / latencyCount.get());
                result.setMaxLatencyMs(maxLatency.get());
            }
            result.setEndTime(LocalDateTime.now());

            task.setStatus("COMPLETED");
            task.setFinishedAt(LocalDateTime.now());

            result.getMetrics().put("processedRecords", processed.get());
            result.getMetrics().put("durationMs",
                    java.time.Duration.between(result.getStartTime(), result.getEndTime()).toMillis());

            resultCache.put(taskId, result);
            webSocketService.sendTaskComplete(taskId, result);
            messageQueueService.sendCheckResultToQueue(result);

            log.info("Full check task {} completed: processed={}, diffs={}, latencyCount={}",
                    taskId, processed.get(), diffCount.get(), latencyCount.get());

        } catch (Exception e) {
            log.error("Full check task {} failed", taskId, e);
            task.setStatus("FAILED");
            task.setFinishedAt(LocalDateTime.now());
            result.setEndTime(LocalDateTime.now());
            webSocketService.sendTaskProgress(taskId, "ERROR", e.getMessage());
        } finally {
            runningTasks.remove(taskId);
        }
    }

    private void executeStratifiedHashCheck(CheckTask task) {
        String taskId = task.getId();
        task.setStatus("RUNNING");
        task.setStartedAt(LocalDateTime.now());
        runningTasks.put(taskId, task);

        log.info("Starting stratified hash check task: {}, type: {}, table: {}",
                taskId, task.getSourceType(), task.getTableName());

        CheckResult result = CheckResult.builder()
                .taskId(taskId)
                .sourceType(task.getSourceType())
                .tableName(task.getTableName())
                .startTime(LocalDateTime.now())
                .diffs(new ArrayList<>())
                .metrics(new ConcurrentHashMap<>())
                .checkMode("STRATIFIED_HASH")
                .build();

        try {
            DataSourceAdapter adapter = adapterFactory.getAdapter(task.getSourceType());
            int stratumCount = task.getStratumCount() != null ? task.getStratumCount() : defaultStratumCount;

            long sourceCount = adapter.getSourceCount(task);
            long targetCount = adapter.getTargetCount(task);
            result.setTotalSourceRecords(sourceCount);
            result.setTotalTargetRecords(targetCount);

            webSocketService.sendTaskProgress(taskId, "INIT",
                    String.format("Source count: %d, Target count: %d, Strata: %d",
                            sourceCount, targetCount, stratumCount));

            AtomicLong processed = new AtomicLong(0);
            AtomicLong diffCount = new AtomicLong(0);
            AtomicLong latencyCount = new AtomicLong(0);
            AtomicLong totalLatency = new AtomicLong(0);
            AtomicLong maxLatency = new AtomicLong(0);
            AtomicLong hashVerified = new AtomicLong(0);
            AtomicLong hashSkipped = new AtomicLong(0);

            List<DataRecord> sourceBatch = new ArrayList<>();
            List<DataRecord> targetBatch = new ArrayList<>();
            Map<String, DataRecord> sourceKeyMap = new HashMap<>();
            Map<String, DataRecord> targetKeyMap = new HashMap<>();

            Iterator<DataRecord> sourceIterator = adapter.iterateSource(task);
            Iterator<DataRecord> targetIterator = adapter.iterateTarget(task);
            int batchSize = thresholdConfig.getEffectiveBatchSize(task);

            while (sourceIterator.hasNext() || targetIterator.hasNext()) {
                sourceBatch.clear();
                targetBatch.clear();
                sourceKeyMap.clear();
                targetKeyMap.clear();

                int sourceRead = 0;
                while (sourceIterator.hasNext() && sourceRead < batchSize) {
                    DataRecord record = sourceIterator.next();
                    if (record != null && record.getKey() != null) {
                        sourceBatch.add(record);
                        sourceKeyMap.put(record.getKey(), record);
                    }
                    sourceRead++;
                }

                int targetRead = 0;
                while (targetIterator.hasNext() && targetRead < batchSize) {
                    DataRecord record = targetIterator.next();
                    if (record != null && record.getKey() != null) {
                        targetBatch.add(record);
                        targetKeyMap.put(record.getKey(), record);
                    }
                    targetRead++;
                }

                StratifiedSampler.StratifiedResult sourceStrata =
                        stratifiedSampler.stratifyByKeyHash(sourceBatch, stratumCount);
                StratifiedSampler.StratifiedResult targetStrata =
                        stratifiedSampler.stratifyByKeyHash(targetBatch, stratumCount);

                Map<String, String> sourceStratumHashes = new LinkedHashMap<>();
                Map<String, String> targetStratumHashes = new LinkedHashMap<>();

                for (int i = 0; i < stratumCount; i++) {
                    String stratumName = "stratum_" + i;
                    List<DataRecord> sourceStratum = sourceStrata.getStrata().size() > i ?
                            sourceStrata.getStrata().get(i) : Collections.emptyList();
                    List<DataRecord> targetStratum = targetStrata.getStrata().size() > i ?
                            targetStrata.getStrata().get(i) : Collections.emptyList();

                    String sourceHash = hashChecker.calculateBatchHash(sourceStratum);
                    String targetHash = hashChecker.calculateBatchHash(targetStratum);
                    sourceStratumHashes.put(stratumName, sourceHash);
                    targetStratumHashes.put(stratumName, targetHash);
                }

                List<String> differentStrata =
                        hashChecker.findDifferentPartitions(sourceStratumHashes, targetStratumHashes);

                result.getMetrics().put("totalStrata", stratumCount);
                result.getMetrics().put("differentStrata", differentStrata.size());

                Set<String> keysToVerify = new HashSet<>();
                for (String stratumName : differentStrata) {
                    int stratumIndex = Integer.parseInt(stratumName.split("_")[1]);
                    List<DataRecord> sourceStratum = sourceStrata.getStrata().size() > stratumIndex ?
                            sourceStrata.getStrata().get(stratumIndex) : Collections.emptyList();
                    List<DataRecord> targetStratum = targetStrata.getStrata().size() > stratumIndex ?
                            targetStrata.getStrata().get(stratumIndex) : Collections.emptyList();

                    for (DataRecord record : sourceStratum) {
                        keysToVerify.add(record.getKey());
                    }
                    for (DataRecord record : targetStratum) {
                        keysToVerify.add(record.getKey());
                    }
                }

                hashVerified.addAndGet(keysToVerify.size());
                hashSkipped.addAndGet(sourceKeyMap.size() + targetKeyMap.size() - keysToVerify.size());

                for (String key : keysToVerify) {
                    DataRecord sourceRecord = sourceKeyMap.get(key);
                    DataRecord targetRecord = targetKeyMap.get(key);

                    if (sourceRecord == null && targetRecord == null) {
                        continue;
                    }

                    if (sourceRecord != null && targetRecord != null &&
                            hashChecker.compareRecordHash(sourceRecord, targetRecord)) {
                        processed.incrementAndGet();
                        continue;
                    }

                    Optional<DiffResult> diffOpt = dataComparator.compare(sourceRecord, targetRecord, task);
                    if (diffOpt.isPresent()) {
                        DiffResult diff = diffOpt.get();
                        result.getDiffs().add(diff);
                        diffCount.incrementAndGet();

                        if (diff.getDiffType().name().contains("LATENCY")) {
                            latencyCount.incrementAndGet();
                            totalLatency.addAndGet(diff.getLatencyMs());
                            maxLatency.set(Math.max(maxLatency.get(), diff.getLatencyMs()));
                        }

                        webSocketService.sendDiff(diff);
                        messageQueueService.sendDiffToQueue(diff);
                        diffCache.put(diff.getId(), diff);
                    }

                    processed.incrementAndGet();
                }

                long currentProcessed = processed.get();
                if (currentProcessed % batchSize == 0) {
                    webSocketService.sendTaskProgress(taskId, "PROCESSING",
                            String.format("Processed: %d, Hash verified: %d, Hash skipped: %d, Diffs: %d",
                                    currentProcessed, hashVerified.get(), hashSkipped.get(), diffCount.get()));
                }
            }

            result.setDiffCount(diffCount.get());
            result.setLatencyCount(latencyCount.get());
            if (latencyCount.get() > 0) {
                result.setAvgLatencyMs((double) totalLatency.get() / latencyCount.get());
                result.setMaxLatencyMs(maxLatency.get());
            }
            result.setEndTime(LocalDateTime.now());

            task.setStatus("COMPLETED");
            task.setFinishedAt(LocalDateTime.now());

            result.getMetrics().put("processedRecords", processed.get());
            result.getMetrics().put("hashVerifiedRecords", hashVerified.get());
            result.getMetrics().put("hashSkippedRecords", hashSkipped.get());
            result.getMetrics().put("durationMs",
                    java.time.Duration.between(result.getStartTime(), result.getEndTime()).toMillis());

            resultCache.put(taskId, result);
            webSocketService.sendTaskComplete(taskId, result);
            messageQueueService.sendCheckResultToQueue(result);

            log.info("Stratified hash check task {} completed: processed={}, hashVerified={}, hashSkipped={}, diffs={}",
                    taskId, processed.get(), hashVerified.get(), hashSkipped.get(), diffCount.get());

        } catch (Exception e) {
            log.error("Stratified hash check task {} failed", taskId, e);
            task.setStatus("FAILED");
            task.setFinishedAt(LocalDateTime.now());
            result.setEndTime(LocalDateTime.now());
            webSocketService.sendTaskProgress(taskId, "ERROR", e.getMessage());
        } finally {
            runningTasks.remove(taskId);
        }
    }

    private DataRecord findTargetRecord(String key, Iterator<DataRecord> targetIterator,
                                        Map<String, DataRecord> targetBuffer,
                                        DataSourceAdapter adapter, CheckTask task) {
        DataRecord buffered = targetBuffer.remove(key);
        if (buffered != null) {
            return buffered;
        }

        while (targetIterator.hasNext()) {
            DataRecord record = targetIterator.next();
            if (record == null || record.getKey() == null) {
                continue;
            }
            if (record.getKey().equals(key)) {
                return record;
            }
            targetBuffer.put(record.getKey(), record);
            if (targetBuffer.size() > 10000) {
                break;
            }
        }

        return adapter.getTargetRecord(key, task);
    }

    public Optional<CheckResult> getResult(String taskId) {
        return Optional.ofNullable(resultCache.getIfPresent(taskId));
    }

    public Collection<CheckTask> getRunningTasks() {
        return Collections.unmodifiableCollection(runningTasks.values());
    }

    public Collection<CheckResult> getRecentResults() {
        return resultCache.asMap().values();
    }

    public boolean cancelTask(String taskId) {
        CheckTask task = runningTasks.remove(taskId);
        if (task != null) {
            task.setStatus("CANCELLED");
            task.setFinishedAt(LocalDateTime.now());
            return true;
        }
        return false;
    }

    public Collection<DiffResult> getAllDiffs() {
        return diffCache.asMap().values();
    }

    public Optional<DiffResult> getDiff(String diffId) {
        return Optional.ofNullable(diffCache.getIfPresent(diffId));
    }

    public void updateDiff(DiffResult diff) {
        diffCache.put(diff.getId(), diff);
    }
}
