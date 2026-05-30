package com.dtmonitor.diagnosis.service;

import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.PressureTestConfig;
import com.dtmonitor.core.model.PressureTestMetrics;
import com.dtmonitor.core.model.PressureTestResult;
import com.dtmonitor.core.model.entity.BranchTransaction;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.service.BranchTransactionService;
import com.dtmonitor.core.service.GlobalTransactionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class PressureTestService {

    private final GlobalTransactionService globalTransactionService;
    private final BranchTransactionService branchTransactionService;

    private final Map<String, PressureTestResult> activeTests = new ConcurrentHashMap<>();
    private final Map<String, Future<?>> testFutures = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(4);

    private static final String[] BUSINESS_TYPES = {"订单支付", "库存扣减", "用户注册", "资金转账", "优惠券核销"};
    private static final String[] RESOURCES = {"jdbc:mysql://db1:3306/order", "jdbc:mysql://db2:3306/inventory", "jdbc:mysql://db3:3306/account", "redis://cache1:6379"};

    public List<PressureTestResult> listAllTests() {
        return new ArrayList<>(activeTests.values());
    }

    public PressureTestResult getTest(String testId) {
        return activeTests.get(testId);
    }

    public PressureTestResult startTest(PressureTestConfig config) {
        String testId = "PT-" + System.currentTimeMillis() + "-" + UUID.randomUUID().toString().substring(0, 8);

        PressureTestResult result = PressureTestResult.builder()
                .testId(testId)
                .config(config)
                .status(PressureTestResult.TestStatus.RUNNING)
                .startTime(LocalDateTime.now())
                .build();

        activeTests.put(testId, result);

        Future<?> future = CompletableFuture.runAsync(() -> runPressureTest(testId, config));
        testFutures.put(testId, future);

        return result;
    }

    public PressureTestResult stopTest(String testId) {
        PressureTestResult result = activeTests.get(testId);
        if (result == null) {
            return null;
        }

        Future<?> future = testFutures.get(testId);
        if (future != null && !future.isDone()) {
            future.cancel(true);
        }

        result.setStatus(PressureTestResult.TestStatus.CANCELLED);
        result.setEndTime(LocalDateTime.now());
        result.setSummary(generateSummary(result));

        return result;
    }

    private void runPressureTest(String testId, PressureTestConfig config) {
        log.info("Starting pressure test: {} with config: {}", testId, config);

        ThreadPoolExecutor executor = new ThreadPoolExecutor(
                config.getConcurrency(),
                config.getConcurrency(),
                0L,
                TimeUnit.MILLISECONDS,
                new LinkedBlockingQueue<>(config.getConcurrency() * 10)
        );

        AtomicLong totalRequests = new AtomicLong(0);
        AtomicLong successCount = new AtomicLong(0);
        AtomicLong failureCount = new AtomicLong(0);
        AtomicLong timeoutCount = new AtomicLong(0);
        AtomicLong rollbackCount = new AtomicLong(0);
        List<Long> responseTimes = Collections.synchronizedList(new ArrayList<>());

        long startTime = System.currentTimeMillis();
        long endTime = startTime + config.getDurationSeconds() * 1000L;

        ScheduledFuture<?> metricsCollector = scheduler.scheduleAtFixedRate(() -> {
            PressureTestMetrics metrics = collectMetrics(
                    totalRequests, successCount, failureCount, timeoutCount,
                    rollbackCount, responseTimes, startTime
            );
            PressureTestResult result = activeTests.get(testId);
            if (result != null) {
                result.getMetrics().add(metrics);
            }
            responseTimes.clear();
        }, 1, 1, TimeUnit.SECONDS);

        try {
            while (System.currentTimeMillis() < endTime && !Thread.currentThread().isInterrupted()) {
                for (int i = 0; i < config.getConcurrency(); i++) {
                    executor.submit(() -> {
                        long reqStart = System.currentTimeMillis();
                        try {
                            boolean success = simulateTransaction(config);
                            totalRequests.incrementAndGet();
                            if (success) {
                                successCount.incrementAndGet();
                            } else {
                                failureCount.incrementAndGet();
                                if (Math.random() < 0.3) {
                                    rollbackCount.incrementAndGet();
                                }
                            }
                        } catch (TimeoutException e) {
                            totalRequests.incrementAndGet();
                            timeoutCount.incrementAndGet();
                            failureCount.incrementAndGet();
                        } catch (Exception e) {
                            totalRequests.incrementAndGet();
                            failureCount.incrementAndGet();
                        } finally {
                            long duration = System.currentTimeMillis() - reqStart;
                            responseTimes.add(duration);
                        }
                    });
                }
                Thread.sleep(100);
            }

            executor.shutdown();
            executor.awaitTermination(30, TimeUnit.SECONDS);
            metricsCollector.cancel(false);

            PressureTestResult result = activeTests.get(testId);
            if (result != null) {
                result.setStatus(PressureTestResult.TestStatus.COMPLETED);
                result.setEndTime(LocalDateTime.now());
                result.setSummary(generateSummary(result));
            }

        } catch (InterruptedException e) {
            log.info("Pressure test cancelled: {}", testId);
            Thread.currentThread().interrupt();
        } catch (Exception e) {
            log.error("Pressure test failed: {}", testId, e);
            PressureTestResult result = activeTests.get(testId);
            if (result != null) {
                result.setStatus(PressureTestResult.TestStatus.FAILED);
                result.setEndTime(LocalDateTime.now());
            }
        } finally {
            metricsCollector.cancel(true);
            testFutures.remove(testId);
        }

        log.info("Pressure test finished: {}", testId);
    }

    private boolean simulateTransaction(PressureTestConfig config) throws TimeoutException {
        try {
            if (config.getNetworkDelayMs() > 0) {
                Thread.sleep((long) (config.getNetworkDelayMs() * (0.5 + Math.random())));
            }

            TransactionMode mode = config.getMode();
            String xid = generateXid();
            String businessType = config.getBusinessType() != null ?
                    config.getBusinessType() :
                    BUSINESS_TYPES[new Random().nextInt(BUSINESS_TYPES.length)];

            GlobalTransaction globalTx = GlobalTransaction.builder()
                    .xid(xid)
                    .applicationId("pressure-test-app")
                    .transactionServiceGroup("pressure-test-group")
                    .mode(mode)
                    .status(TransactionStatus.BEGIN)
                    .beginTime(LocalDateTime.now())
                    .timeoutMs(30000L)
                    .traceId(UUID.randomUUID().toString().replace("-", ""))
                    .businessType(businessType)
                    .trafficColor(generateTrafficColor())
                    .tags(generateTags(businessType, mode))
                    .build();

            int branchCount = 1 + new Random().nextInt(3);
            List<BranchTransaction> branches = new ArrayList<>();
            for (int i = 0; i < branchCount; i++) {
                BranchTransaction branch = BranchTransaction.builder()
                        .branchId(xid + "-" + i)
                        .xid(xid)
                        .resourceId(RESOURCES[i % RESOURCES.length])
                        .status("REGISTERED")
                        .mode(String.valueOf(mode))
                        .applicationId("pressure-test-app")
                        .beginTime(LocalDateTime.now())
                        .build();
                branches.add(branch);
            }

            if (Math.random() < config.getFailureRate()) {
                globalTx.setStatus(TransactionStatus.FAILED);
                globalTx.setRollbackReason(generateRandomError());
                globalTx.setEndTime(LocalDateTime.now());
                branches.forEach(b -> b.setStatus("FAILED"));
                branches.get(new Random().nextInt(branches.size()))
                        .setErrorMessage(generateRandomError());
                return false;
            }

            if (Math.random() < 0.05) {
                throw new TimeoutException("Transaction timeout");
            }

            globalTx.setStatus(TransactionStatus.COMMITTED);
            globalTx.setEndTime(LocalDateTime.now());
            branches.forEach(b -> {
                b.setStatus("COMMITTED");
                b.setEndTime(LocalDateTime.now());
            });

            return true;

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Interrupted", e);
        }
    }

    private PressureTestMetrics collectMetrics(AtomicLong totalRequests,
                                                AtomicLong successCount,
                                                AtomicLong failureCount,
                                                AtomicLong timeoutCount,
                                                AtomicLong rollbackCount,
                                                List<Long> responseTimes,
                                                long startTime) {
        long total = totalRequests.get();
        long success = successCount.get();
        long failure = failureCount.get();
        long timeout = timeoutCount.get();
        long rollback = rollbackCount.get();

        double avgRt = 0;
        double p95 = 0;
        double p99 = 0;

        if (!responseTimes.isEmpty()) {
            List<Long> sorted = new ArrayList<>(responseTimes);
            Collections.sort(sorted);
            avgRt = sorted.stream().mapToLong(Long::longValue).average().orElse(0);
            p95 = sorted.get((int) (sorted.size() * 0.95));
            p99 = sorted.get((int) (sorted.size() * 0.99));
        }

        double tps = total * 1000.0 / (System.currentTimeMillis() - startTime);

        return PressureTestMetrics.builder()
                .totalRequests(total)
                .successCount(success)
                .failureCount(failure)
                .timeoutCount(timeout)
                .avgResponseTimeMs(avgRt)
                .p95ResponseTimeMs(p95)
                .p99ResponseTimeMs(p99)
                .tps(tps)
                .rollbackCount(rollback)
                .timestamp(LocalDateTime.now())
                .build();
    }

    private PressureTestMetrics generateSummary(PressureTestResult result) {
        List<PressureTestMetrics> metrics = result.getMetrics();
        if (metrics == null || metrics.isEmpty()) {
            return PressureTestMetrics.builder()
                    .totalRequests(0)
                    .successCount(0)
                    .failureCount(0)
                    .timeoutCount(0)
                    .rollbackCount(0)
                    .build();
        }

        PressureTestMetrics last = metrics.get(metrics.size() - 1);
        return PressureTestMetrics.builder()
                .totalRequests(last.getTotalRequests())
                .successCount(last.getSuccessCount())
                .failureCount(last.getFailureCount())
                .timeoutCount(last.getTimeoutCount())
                .rollbackCount(last.getRollbackCount())
                .avgResponseTimeMs(metrics.stream().mapToDouble(PressureTestMetrics::getAvgResponseTimeMs).average().orElse(0))
                .p95ResponseTimeMs(metrics.stream().mapToDouble(PressureTestMetrics::getP95ResponseTimeMs).max().orElse(0))
                .p99ResponseTimeMs(metrics.stream().mapToDouble(PressureTestMetrics::getP99ResponseTimeMs).max().orElse(0))
                .tps(metrics.stream().mapToDouble(PressureTestMetrics::getTps).max().orElse(0))
                .timestamp(LocalDateTime.now())
                .build();
    }

    private String generateXid() {
        return "192.168.1." + (100 + new Random().nextInt(100)) + ":8091:" + System.currentTimeMillis() + ":" + UUID.randomUUID().toString().substring(0, 8);
    }

    private String generateTrafficColor() {
        String[] colors = {"RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE", "GRAY"};
        return colors[new Random().nextInt(colors.length)];
    }

    private Map<String, String> generateTags(String businessType, TransactionMode mode) {
        Map<String, String> tags = new HashMap<>();
        tags.put("businessType", businessType);
        tags.put("transactionMode", String.valueOf(mode));
        tags.put("environment", "pressure-test");
        tags.put("version", "v1.0.0");
        return tags;
    }

    private String generateRandomError() {
        String[] errors = {
                "Deadlock found when trying to get lock; try restarting transaction",
                "Connection timed out: connect",
                "java.net.SocketException: Connection reset",
                "java.lang.NullPointerException: null",
                "Duplicate entry '123' for key 'PRIMARY'",
                "Service unavailable: 503 Service Unavailable",
                "Access denied for user 'dbuser'@'%'",
                "Too many connections: pool exhausted",
                "Foreign key constraint fails"
        };
        return errors[new Random().nextInt(errors.length)];
    }
}
