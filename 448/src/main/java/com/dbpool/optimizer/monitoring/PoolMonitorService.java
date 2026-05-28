package com.dbpool.optimizer.monitoring;

import com.dbpool.optimizer.model.*;
import org.springframework.stereotype.Service;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class PoolMonitorService {

    private final Random random = new Random();
    private final List<PoolMonitorSnapshot> snapshotHistory = new CopyOnWriteArrayList<>();
    private final Queue<SlowSqlRecord> slowSqlRecords = new ConcurrentLinkedQueue<>();
    private final List<ConnectionLeakAlert> activeAlerts = new CopyOnWriteArrayList<>();
    private final List<AutoTuningDecision> tuningHistory = new CopyOnWriteArrayList<>();
    private final AtomicLong alertCounter = new AtomicLong(0);

    private volatile PoolConfig currentConfig;
    private volatile WorkloadProfile currentWorkload;
    private volatile boolean monitoring = false;
    private volatile int dynamicMaxPoolSize;
    private volatile int dynamicMinIdle;
    private ScheduledExecutorService scheduler;

    private static final int MAX_SNAPSHOTS = 600;
    private static final int MAX_SLOW_SQL = 500;
    private static final long LEAK_THRESHOLD_MS = 30000;

    public void startMonitoring(PoolConfig config, WorkloadProfile workload) {
        this.currentConfig = config;
        this.currentWorkload = workload;
        this.dynamicMaxPoolSize = config.getMaxPoolSize();
        this.dynamicMinIdle = config.getMinIdle();
        this.monitoring = true;

        if (scheduler != null && !scheduler.isShutdown()) {
            scheduler.shutdownNow();
        }
        scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(this::collectSnapshot, 0, 1, TimeUnit.SECONDS);
    }

    public void stopMonitoring() {
        this.monitoring = false;
        if (scheduler != null) {
            scheduler.shutdownNow();
        }
    }

    public boolean isMonitoring() {
        return monitoring;
    }

    private void collectSnapshot() {
        if (!monitoring || currentConfig == null) return;

        double utilization = simulateUtilization();
        int activeConns = (int) Math.round(dynamicMaxPoolSize * utilization);
        int idleConns = Math.max(0, dynamicMaxPoolSize - activeConns);
        int waitingThreads = simulateWaitingThreads(utilization);

        double avgBorrowTime = simulateBorrowTime(utilization);
        double maxBorrowTime = avgBorrowTime * (1 + random.nextDouble() * 2);
        double avgReturnTime = currentWorkload != null ? currentWorkload.getAvgServiceTimeMs() : 50;
        double avgWaitTime = simulateWaitTime(utilization, waitingThreads);
        double throughput = simulateThroughput(utilization);

        int borrowed = (int) Math.round(throughput * (0.8 + random.nextDouble() * 0.4));
        int returned = (int) Math.round(throughput * (0.8 + random.nextDouble() * 0.4));
        int timeouts = utilization > 0.9 ? random.nextInt(3) : 0;

        PoolMonitorSnapshot snapshot = PoolMonitorSnapshot.builder()
                .timestamp(System.currentTimeMillis())
                .activeConnections(activeConns)
                .idleConnections(idleConns)
                .waitingThreads(waitingThreads)
                .totalConnections(dynamicMaxPoolSize)
                .avgBorrowTimeMs(avgBorrowTime)
                .maxBorrowTimeMs(maxBorrowTime)
                .avgReturnTimeMs(avgReturnTime)
                .avgWaitTimeMs(avgWaitTime)
                .utilization(utilization)
                .throughputLastSecond(throughput)
                .connectionsBorrowed(borrowed)
                .connectionsReturned(returned)
                .connectionTimeouts(timeouts)
                .uptimeMs(0)
                .build();

        snapshotHistory.add(snapshot);
        if (snapshotHistory.size() > MAX_SNAPSHOTS) {
            snapshotHistory.remove(0);
        }

        detectSlowSql(snapshot);
        detectLeaks(snapshot);
    }

    private double simulateUtilization() {
        double base = 0.6;
        double hourOfDay = (System.currentTimeMillis() / 3600000.0) % 24;

        if (hourOfDay >= 9 && hourOfDay <= 11) base = 0.8;
        else if (hourOfDay >= 14 && hourOfDay <= 16) base = 0.75;
        else if (hourOfDay >= 22 || hourOfDay <= 6) base = 0.2;

        if (currentWorkload != null && currentWorkload.getMarkovArrivalConfig() != null
                && currentWorkload.getMarkovArrivalConfig().isEnabled()) {
            double burstiness = currentWorkload.getMarkovArrivalConfig().getBurstinessFactor();
            base += (random.nextDouble() - 0.5) * 0.2 * burstiness;
        } else {
            base += (random.nextDouble() - 0.5) * 0.15;
        }

        return Math.max(0.05, Math.min(0.98, base));
    }

    private int simulateWaitingThreads(double utilization) {
        if (utilization > 0.85) {
            return random.nextInt((int) (utilization * 10));
        } else if (utilization > 0.7) {
            return random.nextInt(3);
        }
        return 0;
    }

    private double simulateBorrowTime(double utilization) {
        double base = 5.0;
        if (currentWorkload != null) {
            base = currentWorkload.getAvgServiceTimeMs() * 0.05;
        }
        if (utilization > 0.8) {
            base *= (1 + (utilization - 0.8) * 5);
        }
        return Math.max(1, base + random.nextGaussian() * 2);
    }

    private double simulateWaitTime(double utilization, int waitingThreads) {
        if (waitingThreads == 0) return 0;
        double baseWait = 10.0 + waitingThreads * 5.0;
        if (utilization > 0.9) baseWait *= 3;
        return Math.max(0, baseWait + random.nextGaussian() * 10);
    }

    private double simulateThroughput(double utilization) {
        if (currentWorkload == null) return 50.0;
        double baseRate = currentWorkload.getArrivalRate();
        if (utilization > 0.9) {
            return baseRate * (1 - (utilization - 0.9) * 3);
        }
        return baseRate * (0.9 + utilization * 0.1);
    }

    private void detectSlowSql(PoolMonitorSnapshot snapshot) {
        if (currentWorkload == null) return;

        boolean hasSlowSql = random.nextDouble() < 0.15;
        if (!hasSlowSql) return;

        boolean isLong = currentWorkload.getMixedTransactionConfig() != null
                && currentWorkload.getMixedTransactionConfig().isEnabled()
                && random.nextDouble() > currentWorkload.getMixedTransactionConfig().getShortQueryRatio();

        double executionTime;
        String sqlType;
        String sqlPreview;

        if (isLong) {
            executionTime = 500 + random.nextDouble() * 2000;
            sqlType = random.nextBoolean() ? "SELECT" : "UPDATE";
            sqlPreview = sqlType.equals("SELECT")
                    ? "SELECT * FROM orders WHERE create_time > ? GROUP BY user_id..."
                    : "UPDATE user_stats SET count = (SELECT COUNT(*)...) WHERE...";
        } else {
            executionTime = currentWorkload.getAvgServiceTimeMs() * (2 + random.nextDouble() * 3);
            sqlType = random.nextBoolean() ? "SELECT" : "INSERT";
            sqlPreview = sqlType.equals("SELECT")
                    ? "SELECT id, name FROM users WHERE id = ?"
                    : "INSERT INTO access_log (user_id, action) VALUES (?, ?)";
        }

        double borrowTime = snapshot.getAvgBorrowTimeMs() * (0.5 + random.nextDouble());
        double holdTime = executionTime + borrowTime;
        double waitTime = snapshot.getAvgWaitTimeMs();

        boolean isLongTx = holdTime > LEAK_THRESHOLD_MS / 2;
        boolean isLeak = holdTime > LEAK_THRESHOLD_MS;

        SlowSqlRecord record = SlowSqlRecord.builder()
                .timestamp(System.currentTimeMillis())
                .sqlId("SQL-" + UUID.randomUUID().toString().substring(0, 8))
                .sqlType(sqlType)
                .sqlPreview(sqlPreview)
                .executionTimeMs(executionTime)
                .borrowTimeMs(borrowTime)
                .holdTimeMs(holdTime)
                .waitTimeMs(waitTime)
                .connectionId(random.nextInt(dynamicMaxPoolSize))
                .isLongTransaction(isLongTx)
                .isPotentialLeak(isLeak)
                .threadName("worker-" + random.nextInt(20))
                .stackTraceHint(isLongTx ? "com.service.OrderService.processBatch()" : "com.dao.UserDao.findById()")
                .build();

        slowSqlRecords.add(record);
        while (slowSqlRecords.size() > MAX_SLOW_SQL) {
            slowSqlRecords.poll();
        }
    }

    private void detectLeaks(PoolMonitorSnapshot snapshot) {
        Iterator<SlowSqlRecord> it = slowSqlRecords.iterator();
        while (it.hasNext()) {
            SlowSqlRecord record = it.next();
            if (record.isPotentialLeak() && !isAlreadyAlerted(record.getSqlId())) {
                ConnectionLeakAlert alert = ConnectionLeakAlert.builder()
                        .timestamp(System.currentTimeMillis())
                        .alertId("ALERT-" + alertCounter.incrementAndGet())
                        .severity(snapshot.getUtilization() > 0.9 ? "CRITICAL" : "WARNING")
                        .message(String.format("连接 #%d 可能泄漏：持有时间 %.0fms 超过阈值 %dms，SQL: %s",
                                record.getConnectionId(), record.getHoldTimeMs(), LEAK_THRESHOLD_MS,
                                record.getSqlPreview()))
                        .connectionId(record.getConnectionId())
                        .holdDurationMs((long) record.getHoldTimeMs())
                        .borrowTimestamp(record.getTimestamp() - (long) record.getHoldTimeMs())
                        .threadName(record.getThreadName())
                        .sqlPreview(record.getSqlPreview())
                        .poolUtilizationAtAlert(snapshot.getUtilization())
                        .activeConnectionsAtAlert(snapshot.getActiveConnections())
                        .recommendations(generateLeakRecommendations(record, snapshot))
                        .acknowledged(false)
                        .build();

                activeAlerts.add(alert);
                if (activeAlerts.size() > 100) {
                    activeAlerts.remove(0);
                }
            }
        }
    }

    private boolean isAlreadyAlerted(String sqlId) {
        return activeAlerts.stream()
                .anyMatch(a -> a.getSqlPreview() != null && a.getSqlPreview().contains(sqlId));
    }

    private List<String> generateLeakRecommendations(SlowSqlRecord record, PoolMonitorSnapshot snapshot) {
        List<String> recs = new ArrayList<>();
        recs.add("检查代码中是否正确关闭了数据库连接（try-with-resources）");

        if (record.isLongTransaction()) {
            recs.add("长事务检测：考虑拆分大事务为多个小事务");
            recs.add("检查是否存在未提交的事务或遗漏的 commit/rollback");
        }

        if (snapshot.getUtilization() > 0.85) {
            recs.add("当前连接池利用率过高，连接泄漏影响加剧，建议优先排查泄漏");
        }

        if (record.getExecutionTimeMs() > 1000) {
            recs.add(String.format("SQL执行时间 %.0fms 过长，建议优化查询或添加索引", record.getExecutionTimeMs()));
        }

        if (currentConfig != null && currentConfig.getLeakDetectionThresholdMs() <= 0) {
            recs.add("建议启用连接池泄漏检测参数（leakDetectionThreshold）");
        }

        return recs;
    }

    public List<PoolMonitorSnapshot> getRecentSnapshots(int count) {
        int size = snapshotHistory.size();
        if (size <= count) return new ArrayList<>(snapshotHistory);
        return new ArrayList<>(snapshotHistory.subList(size - count, size));
    }

    public PoolMonitorSnapshot getLatestSnapshot() {
        return snapshotHistory.isEmpty() ? null : snapshotHistory.get(snapshotHistory.size() - 1);
    }

    public List<SlowSqlRecord> getSlowSqlRecords(int limit) {
        List<SlowSqlRecord> records = new ArrayList<>(slowSqlRecords);
        if (records.size() <= limit) return records;
        return records.subList(records.size() - limit, records.size());
    }

    public SlowSqlAnalysis analyzeSlowSql() {
        List<SlowSqlRecord> records = new ArrayList<>(slowSqlRecords);
        if (records.isEmpty()) {
            return SlowSqlAnalysis.builder()
                    .totalSlowQueries(0)
                    .leakRiskScore(0)
                    .leakRiskLevel("LOW")
                    .topSlowQueries(Collections.emptyList())
                    .slowQueryTypeDistribution(Collections.emptyMap())
                    .slowQueryByHour(Collections.emptyMap())
                    .analysisSummary(Collections.singletonList("暂无慢SQL记录"))
                    .activeAlerts(Collections.emptyList())
                    .build();
        }

        int totalSlow = records.size();
        double avgTime = records.stream().mapToDouble(SlowSqlRecord::getExecutionTimeMs).average().orElse(0);
        double maxTime = records.stream().mapToDouble(SlowSqlRecord::getExecutionTimeMs).max().orElse(0);
        double avgBorrow = records.stream().mapToDouble(SlowSqlRecord::getBorrowTimeMs).average().orElse(0);
        double avgHold = records.stream().mapToDouble(SlowSqlRecord::getHoldTimeMs).average().orElse(0);

        long longTxCount = records.stream().filter(SlowSqlRecord::isLongTransaction).count();
        long leakCount = records.stream().filter(SlowSqlRecord::isPotentialLeak).count();

        double leakRiskScore = Math.min(100, (leakCount * 20 + longTxCount * 5));
        String riskLevel = leakRiskScore > 60 ? "HIGH" : leakRiskScore > 30 ? "MEDIUM" : "LOW";

        double correlation = calculatePoolPressureCorrelation(records);

        List<SlowSqlRecord> topSlow = records.stream()
                .sorted((a, b) -> Double.compare(b.getExecutionTimeMs(), a.getExecutionTimeMs()))
                .limit(10)
                .toList();

        Map<String, Integer> typeDist = new HashMap<>();
        records.forEach(r -> typeDist.merge(r.getSqlType(), 1, Integer::sum));

        List<String> summary = new ArrayList<>();
        summary.add(String.format("共检测到 %d 条慢SQL，平均执行时间 %.1fms", totalSlow, avgTime));
        if (longTxCount > 0) {
            summary.add(String.format("其中 %d 条为长事务（持有连接超过阈值）", longTxCount));
        }
        if (leakCount > 0) {
            summary.add(String.format("⚠️ %d 条疑似连接泄漏，泄漏风险评分 %.0f（%s）", leakCount, leakRiskScore, riskLevel));
        }
        if (correlation > 0.6) {
            summary.add(String.format("慢SQL与连接池压力相关性 %.2f 较高，慢SQL是连接池压力的主要来源", correlation));
        }

        return SlowSqlAnalysis.builder()
                .totalSlowQueries(totalSlow)
                .avgSlowQueryTimeMs(avgTime)
                .maxSlowQueryTimeMs(maxTime)
                .avgBorrowTimeForSlowMs(avgBorrow)
                .avgHoldTimeForSlowMs(avgHold)
                .correlationWithPoolPressure(correlation)
                .leakRiskScore(leakRiskScore)
                .leakRiskLevel(riskLevel)
                .topSlowQueries(topSlow)
                .slowQueryTypeDistribution(typeDist)
                .analysisSummary(summary)
                .activeAlerts(new ArrayList<>(activeAlerts))
                .build();
    }

    private double calculatePoolPressureCorrelation(List<SlowSqlRecord> records) {
        if (snapshotHistory.size() < 10 || records.size() < 5) return 0.5;

        List<PoolMonitorSnapshot> recent = snapshotHistory;
        double avgUtil = recent.stream().mapToDouble(PoolMonitorSnapshot::getUtilization).average().orElse(0.5);

        int highUtilSlowCount = 0;
        int totalSample = Math.min(records.size(), 50);
        for (int i = 0; i < totalSample; i++) {
            SlowSqlRecord r = records.get(records.size() - 1 - i);
            long snapTime = r.getTimestamp() / 1000;
            double snapUtil = recent.stream()
                    .filter(s -> Math.abs(s.getTimestamp() / 1000 - snapTime) < 2)
                    .mapToDouble(PoolMonitorSnapshot::getUtilization)
                    .findFirst().orElse(avgUtil);
            if (snapUtil > 0.7) highUtilSlowCount++;
        }

        return totalSample > 0 ? (double) highUtilSlowCount / totalSample : 0.5;
    }

    public List<ConnectionLeakAlert> getActiveAlerts() {
        return new ArrayList<>(activeAlerts);
    }

    public void acknowledgeAlert(String alertId) {
        activeAlerts.stream()
                .filter(a -> a.getAlertId().equals(alertId))
                .forEach(a -> a.setAcknowledged(true));
    }

    public int getDynamicMaxPoolSize() {
        return dynamicMaxPoolSize;
    }

    public int getDynamicMinIdle() {
        return dynamicMinIdle;
    }

    public List<AutoTuningDecision> getTuningHistory() {
        return new ArrayList<>(tuningHistory);
    }

    public void applyTuning(AutoTuningDecision decision) {
        if ("SCALE_UP".equals(decision.getAction())) {
            dynamicMaxPoolSize = decision.getNewValue();
        } else if ("SCALE_DOWN".equals(decision.getAction())) {
            dynamicMaxPoolSize = decision.getNewValue();
        } else if ("ADJUST_MIN_IDLE".equals(decision.getAction())) {
            dynamicMinIdle = decision.getNewValue();
        }
        decision.setApplied(true);
        tuningHistory.add(decision);
        if (tuningHistory.size() > 200) {
            tuningHistory.remove(0);
        }
    }
}
