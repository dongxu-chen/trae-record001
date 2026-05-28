package com.example.deduplication.stats;

import com.example.deduplication.config.DeduplicationProperties;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.ConcurrentLinkedQueue;

@Slf4j
@Service
@RequiredArgsConstructor
public class QpsStatisticsService {

    private final DeduplicationProperties properties;

    private final AtomicLong requestCount = new AtomicLong(0);
    private final ConcurrentLinkedQueue<Long> requestTimestamps = new ConcurrentLinkedQueue<>();

    private volatile double currentQps = 0.0;

    @PostConstruct
    public void init() {
        log.info("QPS Statistics service initialized");
    }

    public void recordRequest() {
        requestCount.incrementAndGet();
        requestTimestamps.offer(System.currentTimeMillis());
    }

    public double getCurrentQps() {
        return currentQps;
    }

    @Scheduled(fixedRate = 1000)
    public void calculateQps() {
        long windowSeconds = properties.getDynamicWindow().getStatisticsWindowSeconds();
        long cutoffTime = System.currentTimeMillis() - (windowSeconds * 1000);

        while (!requestTimestamps.isEmpty() && requestTimestamps.peek() < cutoffTime) {
            requestTimestamps.poll();
        }

        int recentCount = requestTimestamps.size();
        currentQps = (double) recentCount / windowSeconds;

        log.debug("Current QPS: {:.2f}, window: {}s", currentQps, windowSeconds);
    }

    public long getTotalRequests() {
        return requestCount.get();
    }

    public void reset() {
        requestCount.set(0);
        requestTimestamps.clear();
        currentQps = 0.0;
    }
}
