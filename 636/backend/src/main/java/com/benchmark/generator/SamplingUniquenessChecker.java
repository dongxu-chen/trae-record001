package com.benchmark.generator;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
public class SamplingUniquenessChecker {

    private final BloomFilter bloomFilter;
    private final Set<String> sampledIds;
    private final int sampleSize;
    private final AtomicLong totalGenerated = new AtomicLong(0);
    private final AtomicLong bloomFilterDuplicates = new AtomicLong(0);
    private final AtomicLong sampleDuplicates = new AtomicLong(0);
    private final AtomicLong falsePositives = new AtomicLong(0);
    private final Set<String> sampleSet = ConcurrentHashMap.newKeySet();
    private final Random random = new Random();

    @Getter
    private final Set<String> confirmedDuplicates = ConcurrentHashMap.newKeySet();
    private final Map<String, AtomicLong> duplicateCounts = new ConcurrentHashMap<>();

    private final long samplingInterval;
    private final double samplingRate;

    public SamplingUniquenessChecker(long expectedInsertions, int sampleSize, double falsePositiveProbability) {
        this.bloomFilter = new BloomFilter(expectedInsertions, falsePositiveProbability);
        this.sampleSize = sampleSize;
        this.sampledIds = Collections.synchronizedList(new ArrayList<>(sampleSize));
        this.samplingInterval = Math.max(1, expectedInsertions / sampleSize);
        this.samplingRate = (double) sampleSize / expectedInsertions;
    }

    public boolean checkAndRecord(String id) {
        long count = totalGenerated.incrementAndGet();

        boolean isBloomDuplicate = bloomFilter.put(id);
        if (isBloomDuplicate) {
            bloomFilterDuplicates.incrementAndGet();
        }

        if (shouldSample(count)) {
            boolean isSampleDuplicate = !sampleSet.add(id);
            if (isSampleDuplicate) {
                sampleDuplicates.incrementAndGet();
                confirmedDuplicates.add(id);
                duplicateCounts.computeIfAbsent(id, k -> new AtomicLong(0)).incrementAndGet();
            } else if (sampledIds.size() < sampleSize) {
                sampledIds.add(id);
            }

            if (isBloomDuplicate && !isSampleDuplicate) {
                falsePositives.incrementAndGet();
            }
        }

        return isBloomDuplicate;
    }

    private boolean shouldSample(long count) {
        if (sampledIds.size() < sampleSize / 10) {
            return count % Math.max(1, samplingInterval / 10) == 0;
        }
        if (sampledIds.size() < sampleSize / 2) {
            return count % Math.max(1, samplingInterval / 2) == 0;
        }
        return random.nextDouble() < samplingRate;
    }

    public UniquenessResult getResult() {
        long total = totalGenerated.get();
        long bloomDup = bloomFilterDuplicates.get();
        long sampleDup = sampleDuplicates.get();
        long falsePos = falsePositives.get();

        double estimatedDuplicateRate = total > 0
            ? (double) bloomDup / total
            : 0;

        double sampleDuplicateRate = total > 0
            ? (double) sampleDup / sampleSet.size()
            : 0;

        double adjustedDuplicateRate = (estimatedDuplicateRate + sampleDuplicateRate) / 2;

        return new UniquenessResult(
            total,
            bloomDup,
            sampleDup,
            sampleSet.size(),
            falsePos,
            estimatedDuplicateRate,
            sampleDuplicateRate,
            adjustedDuplicateRate,
            bloomDup - falsePos == 0 && sampleDup == 0,
            new ArrayList<>(sampledIds),
            new ArrayList<>(confirmedDuplicates),
            getDuplicateDetails(),
            bloomFilter.getMemoryUsageBytes()
        );
    }

    private List<DuplicateDetail> getDuplicateDetails() {
        List<DuplicateDetail> details = new ArrayList<>();
        duplicateCounts.forEach((id, count) -> {
            details.add(new DuplicateDetail(id, count.get()));
        });
        details.sort((a, b) -> Long.compare(b.count, a.count));
        return details.subList(0, Math.min(100, details.size()));
    }

    @lombok.Data
    @lombok.AllArgsConstructor
    public static class UniquenessResult {
        private long totalGenerated;
        private long bloomFilterDuplicates;
        private long sampleDuplicates;
        private long sampleSize;
        private long falsePositives;
        private double estimatedDuplicateRate;
        private double sampleDuplicateRate;
        private double adjustedDuplicateRate;
        private boolean isUnique;
        private List<String> sampledIds;
        private List<String> confirmedDuplicateIds;
        private List<DuplicateDetail> duplicateDetails;
        private long memoryUsageBytes;
    }

    @lombok.Data
    @lombok.AllArgsConstructor
    public static class DuplicateDetail {
        private String id;
        private long count;
    }
}
