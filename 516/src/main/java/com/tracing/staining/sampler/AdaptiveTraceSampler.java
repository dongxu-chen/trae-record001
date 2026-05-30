package com.tracing.staining.sampler;

import com.tracing.staining.context.StainingContext;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Component
public class AdaptiveTraceSampler implements TraceSampler {

    @Value("${tracing.sample.rate:1.0}")
    private double baseSampleRate;

    @Value("${tracing.sample.min-rate:0.1}")
    private double minSampleRate;

    @Value("${tracing.sample.max-rate:1.0}")
    private double maxSampleRate;

    @Value("${tracing.sample.adjust-interval-ms:5000}")
    private long adjustIntervalMs;

    @Value("${tracing.sample.qps-high-threshold:1000}")
    private int qpsHighThreshold;

    @Value("${tracing.sample.qps-low-threshold:100}")
    private int qpsLowThreshold;

    @Value("${tracing.sample.concurrency-high-threshold:200}")
    private int concurrencyHighThreshold;

    @Value("${tracing.sample.concurrency-low-threshold:50}")
    private int concurrencyLowThreshold;

    @Value("${tracing.staining.rate:0.1}")
    private double stainingRate;

    @Value("${tracing.staining.user-ids:}")
    private Set<String> stainingUserIds;

    @Value("${tracing.staining.biz-types:}")
    private Set<String> stainingBizTypes;

    @Value("${tracing.staining.paths:}")
    private List<String> stainingPaths;

    private volatile double currentSampleRate;
    private volatile double currentStainingRate;

    private final AtomicLong requestCounter = new AtomicLong(0);
    private final AtomicInteger concurrentRequests = new AtomicInteger(0);
    private final AtomicLong lastQps = new AtomicLong(0);

    private ScheduledExecutorService scheduler;

    private static final String[] COLORS = {"RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE"};

    @PostConstruct
    public void init() {
        currentSampleRate = baseSampleRate;
        currentStainingRate = stainingRate;

        scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread thread = new Thread(r, "adaptive-sampler-scheduler");
            thread.setDaemon(true);
            return thread;
        });

        scheduler.scheduleAtFixedRate(
                this::adjustSampleRate,
                adjustIntervalMs,
                adjustIntervalMs,
                TimeUnit.MILLISECONDS
        );

        log.info("AdaptiveTraceSampler initialized: baseSampleRate={}, minSampleRate={}, maxSampleRate={}",
                baseSampleRate, minSampleRate, maxSampleRate);
    }

    @PreDestroy
    public void destroy() {
        if (scheduler != null) {
            scheduler.shutdownNow();
        }
    }

    public void incrementRequest() {
        requestCounter.incrementAndGet();
        concurrentRequests.incrementAndGet();
    }

    public void decrementRequest() {
        concurrentRequests.decrementAndGet();
    }

    private void adjustSampleRate() {
        try {
            long requestsInInterval = requestCounter.getAndSet(0);
            long currentQps = requestsInInterval * 1000 / adjustIntervalMs;
            int currentConcurrency = concurrentRequests.get();

            lastQps.set(currentQps);

            double oldSampleRate = currentSampleRate;
            double oldStainingRate = currentStainingRate;

            if (currentQps > qpsHighThreshold || currentConcurrency > concurrencyHighThreshold) {
                currentSampleRate = Math.max(minSampleRate, currentSampleRate * 0.8);
                currentStainingRate = Math.max(0.01, currentStainingRate * 0.8);
                log.info("High load detected - QPS={}, Concurrency={}, reducing sample rate: {} -> {}, staining rate: {} -> {}",
                        currentQps, currentConcurrency,
                        String.format("%.2f", oldSampleRate), String.format("%.2f", currentSampleRate),
                        String.format("%.2f", oldStainingRate), String.format("%.2f", currentStainingRate));
            } else if (currentQps < qpsLowThreshold && currentConcurrency < concurrencyLowThreshold) {
                currentSampleRate = Math.min(maxSampleRate, currentSampleRate * 1.2);
                currentStainingRate = Math.min(1.0, currentStainingRate * 1.2);
                log.info("Low load detected - QPS={}, Concurrency={}, increasing sample rate: {} -> {}, staining rate: {} -> {}",
                        currentQps, currentConcurrency,
                        String.format("%.2f", oldSampleRate), String.format("%.2f", currentSampleRate),
                        String.format("%.2f", oldStainingRate), String.format("%.2f", currentStainingRate));
            } else {
                currentSampleRate = baseSampleRate;
                currentStainingRate = stainingRate;
                if (oldSampleRate != baseSampleRate) {
                    log.info("Normal load detected - QPS={}, Concurrency={}, resetting sample rate to base: {} -> {}",
                            currentQps, currentConcurrency,
                            String.format("%.2f", oldSampleRate), String.format("%.2f", currentSampleRate));
                }
            }

        } catch (Exception e) {
            log.error("Failed to adjust sample rate", e);
        }
    }

    @Override
    public boolean shouldSample(HttpServletRequest request, StainingContext context) {
        incrementRequest();

        if (context != null && context.getSampled() != null) {
            return context.getSampled();
        }

        if (isStainingRequest(request, context)) {
            return true;
        }

        if (currentSampleRate >= 1.0) {
            return true;
        }

        if (currentSampleRate <= 0) {
            return false;
        }

        double random = ThreadLocalRandom.current().nextDouble();
        boolean sampled = random < currentSampleRate;

        log.debug("Adaptive sampling decision: random={}, rate={}, sampled={}, qps={}, concurrency={}",
                String.format("%.4f", random), String.format("%.2f", currentSampleRate),
                sampled, lastQps.get(), concurrentRequests.get());

        return sampled;
    }

    @Override
    public boolean shouldStain(HttpServletRequest request, StainingContext context) {
        if (context != null && Boolean.TRUE.equals(context.getStainingFlag())) {
            return true;
        }

        if (isStainingRequest(request, context)) {
            return true;
        }

        if (currentStainingRate >= 1.0) {
            return true;
        }

        if (currentStainingRate <= 0) {
            return false;
        }

        double random = ThreadLocalRandom.current().nextDouble();
        boolean shouldStain = random < currentStainingRate;

        log.debug("Adaptive staining decision: random={}, rate={}, shouldStain={}, qps={}, concurrency={}",
                String.format("%.4f", random), String.format("%.2f", currentStainingRate),
                shouldStain, lastQps.get(), concurrentRequests.get());

        return shouldStain;
    }

    @Override
    public String assignStainingColor(HttpServletRequest request, StainingContext context) {
        if (context != null && context.getStainingColor() != null) {
            return context.getStainingColor();
        }

        if (context != null && context.getUserId() != null && !stainingUserIds.isEmpty()) {
            if (stainingUserIds.contains(context.getUserId())) {
                return "RED";
            }
        }

        if (context != null && context.getBizType() != null && !stainingBizTypes.isEmpty()) {
            if (stainingBizTypes.contains(context.getBizType())) {
                return "BLUE";
            }
        }

        Random random = new Random();
        return COLORS[random.nextInt(COLORS.length)];
    }

    private boolean isStainingRequest(HttpServletRequest request, StainingContext context) {
        if (context != null && context.getUserId() != null && !stainingUserIds.isEmpty()) {
            if (stainingUserIds.contains(context.getUserId())) {
                log.debug("Staining by user ID: {}", context.getUserId());
                return true;
            }
        }

        if (context != null && context.getBizType() != null && !stainingBizTypes.isEmpty()) {
            if (stainingBizTypes.contains(context.getBizType())) {
                log.debug("Staining by biz type: {}", context.getBizType());
                return true;
            }
        }

        if (request != null && !stainingPaths.isEmpty()) {
            String path = request.getRequestURI();
            for (String stainingPath : stainingPaths) {
                if (path.startsWith(stainingPath)) {
                    log.debug("Staining by path: {}", path);
                    return true;
                }
            }
        }

        if (request != null) {
            String stainingFlagHeader = request.getHeader("X-Staining-Flag");
            if ("true".equalsIgnoreCase(stainingFlagHeader)) {
                log.debug("Staining by header flag");
                return true;
            }
        }

        return false;
    }

    public double getCurrentSampleRate() {
        return currentSampleRate;
    }

    public double getCurrentStainingRate() {
        return currentStainingRate;
    }

    public long getCurrentQps() {
        return lastQps.get();
    }

    public int getCurrentConcurrency() {
        return concurrentRequests.get();
    }

    public SamplerStatus getStatus() {
        return new SamplerStatus(
                currentSampleRate,
                currentStainingRate,
                lastQps.get(),
                concurrentRequests.get(),
                baseSampleRate,
                minSampleRate,
                maxSampleRate,
                qpsHighThreshold,
                qpsLowThreshold,
                concurrencyHighThreshold,
                concurrencyLowThreshold
        );
    }

    public static class SamplerStatus {
        private final double currentSampleRate;
        private final double currentStainingRate;
        private final long currentQps;
        private final int currentConcurrency;
        private final double baseSampleRate;
        private final double minSampleRate;
        private final double maxSampleRate;
        private final int qpsHighThreshold;
        private final int qpsLowThreshold;
        private final int concurrencyHighThreshold;
        private final int concurrencyLowThreshold;

        public SamplerStatus(double currentSampleRate, double currentStainingRate,
                             long currentQps, int currentConcurrency,
                             double baseSampleRate, double minSampleRate,
                             double maxSampleRate, int qpsHighThreshold,
                             int qpsLowThreshold, int concurrencyHighThreshold,
                             int concurrencyLowThreshold) {
            this.currentSampleRate = currentSampleRate;
            this.currentStainingRate = currentStainingRate;
            this.currentQps = currentQps;
            this.currentConcurrency = currentConcurrency;
            this.baseSampleRate = baseSampleRate;
            this.minSampleRate = minSampleRate;
            this.maxSampleRate = maxSampleRate;
            this.qpsHighThreshold = qpsHighThreshold;
            this.qpsLowThreshold = qpsLowThreshold;
            this.concurrencyHighThreshold = concurrencyHighThreshold;
            this.concurrencyLowThreshold = concurrencyLowThreshold;
        }

        public double getCurrentSampleRate() { return currentSampleRate; }
        public double getCurrentStainingRate() { return currentStainingRate; }
        public long getCurrentQps() { return currentQps; }
        public int getCurrentConcurrency() { return currentConcurrency; }
        public double getBaseSampleRate() { return baseSampleRate; }
        public double getMinSampleRate() { return minSampleRate; }
        public double getMaxSampleRate() { return maxSampleRate; }
        public int getQpsHighThreshold() { return qpsHighThreshold; }
        public int getQpsLowThreshold() { return qpsLowThreshold; }
        public int getConcurrencyHighThreshold() { return concurrencyHighThreshold; }
        public int getConcurrencyLowThreshold() { return concurrencyLowThreshold; }
    }
}
