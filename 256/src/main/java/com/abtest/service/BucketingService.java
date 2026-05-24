package com.abtest.service;

import com.abtest.dto.BucketAssignmentDTO;
import com.abtest.entity.Experiment;
import com.abtest.entity.Variant;
import com.abtest.repository.ExperimentRepository;
import com.abtest.util.ConsistentHashRing;
import com.google.common.hash.Hashing;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class BucketingService {

    private static final int TOTAL_BUCKETS = 10000;
    private static final String BUCKET_CACHE_PREFIX = "abtest:bucket:";
    private static final String ENTRY_TIME_PREFIX = "abtest:entry_time:";
    private static final long CACHE_TTL_HOURS = 24;

    private final ExperimentRepository experimentRepository;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ClickHouseMetricsService clickHouseMetricsService;

    private final Map<Long, ConsistentHashRing<Variant>> experimentHashRings = new ConcurrentHashMap<>();

    public BucketAssignmentDTO assignUser(String userId, Long experimentId) {
        String cacheKey = BUCKET_CACHE_PREFIX + experimentId + ":" + userId;
        BucketAssignmentDTO cached = (BucketAssignmentDTO) redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            return cached;
        }

        Experiment experiment = experimentRepository.findById(experimentId)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + experimentId));

        if (experiment.getStatus() != Experiment.ExperimentStatus.RUNNING) {
            throw new IllegalStateException("实验未运行: " + experimentId);
        }

        int bucket = calculateBucket(userId, experiment.getTrafficKey());
        int trafficThreshold = (experiment.getTrafficPercentage() * TOTAL_BUCKETS) / 100;

        if (bucket >= trafficThreshold) {
            Variant controlVariant = findControlVariant(experiment.getVariants())
                .orElse(experiment.getVariants().get(0));
            BucketAssignmentDTO assignment = createAssignment(userId, experiment, controlVariant, bucket);
            return assignment;
        }

        ConsistentHashRing<Variant> hashRing = getOrCreateHashRing(experiment);
        Variant assignedVariant = hashRing.getNode(bucket);
        if (assignedVariant == null) {
            assignedVariant = experiment.getVariants().get(0);
        }

        BucketAssignmentDTO assignment = createAssignment(userId, experiment, assignedVariant, bucket);

        redisTemplate.opsForValue().set(cacheKey, assignment, CACHE_TTL_HOURS, TimeUnit.HOURS);
        recordEntryTime(experimentId, userId);

        try {
            clickHouseMetricsService.recordUserAssignment(
                userId, experimentId, assignedVariant.getName(), bucket);
        } catch (Exception e) {
            log.warn("Failed to record user assignment to ClickHouse: userId={}, experimentId={}",
                userId, experimentId, e);
        }

        return assignment;
    }

    private ConsistentHashRing<Variant> getOrCreateHashRing(Experiment experiment) {
        return experimentHashRings.computeIfAbsent(experiment.getId(), id -> {
            ConsistentHashRing<Variant> ring = new ConsistentHashRing<>(100);
            rebuildHashRing(ring, experiment.getVariants());
            return ring;
        });
    }

    private void rebuildHashRing(ConsistentHashRing<Variant> ring, List<Variant> variants) {
        ring.updateNodes(Collections.emptyList());

        for (Variant variant : variants) {
            int weight = variant.getTrafficWeight();
            for (int i = 0; i < weight; i++) {
                String nodeKey = variant.getId() + "-" + i;
                ring.addNode(new WeightedVariantNode(variant, nodeKey));
            }
        }

        log.info("Rebuilt hash ring for experiment: {}, nodes: {}",
            variants.size(), ring.size());
    }

    public void refreshHashRing(Long experimentId) {
        Experiment experiment = experimentRepository.findById(experimentId).orElse(null);
        if (experiment != null) {
            ConsistentHashRing<Variant> ring = experimentHashRings.get(experimentId);
            if (ring != null) {
                rebuildHashRing(ring, experiment.getVariants());
            }
        }
    }

    private static class WeightedVariantNode extends Variant {
        private final String nodeKey;

        public WeightedVariantNode(Variant variant, String nodeKey) {
            this.setId(variant.getId());
            this.setName(variant.getName());
            this.setTrafficWeight(variant.getTrafficWeight());
            this.setIsControl(variant.getIsControl());
            this.setConfiguration(variant.getConfiguration());
            this.setExperiment(variant.getExperiment());
            this.nodeKey = nodeKey;
        }

        @Override
        public String toString() {
            return nodeKey;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (!(o instanceof WeightedVariantNode that)) return false;
            return Objects.equals(nodeKey, that.nodeKey);
        }

        @Override
        public int hashCode() {
            return Objects.hash(nodeKey);
        }
    }

    private int calculateBucket(String userId, String trafficKey) {
        String combined = userId + ":" + trafficKey;
        int hash = Hashing.murmur3_32_fixed().hashString(combined, StandardCharsets.UTF_8).asInt();
        return Math.abs(hash) % TOTAL_BUCKETS;
    }

    private Optional<Variant> findControlVariant(List<Variant> variants) {
        return variants.stream()
            .filter(Variant::getIsControl)
            .findFirst();
    }

    private BucketAssignmentDTO createAssignment(String userId, Experiment experiment,
                                                  Variant variant, int bucket) {
        return new BucketAssignmentDTO(
            userId,
            experiment.getId(),
            experiment.getName(),
            variant.getName(),
            variant.getConfiguration(),
            variant.getIsControl(),
            bucket
        );
    }

    private void recordEntryTime(Long experimentId, String userId) {
        String key = ENTRY_TIME_PREFIX + experimentId + ":" + userId;
        redisTemplate.opsForValue().set(key, LocalDateTime.now().toString(), CACHE_TTL_HOURS, TimeUnit.HOURS);
    }

    public LocalDateTime getUserEntryTime(Long experimentId, String userId) {
        String key = ENTRY_TIME_PREFIX + experimentId + ":" + userId;
        Object value = redisTemplate.opsForValue().get(key);
        if (value instanceof String timeStr) {
            try {
                return LocalDateTime.parse(timeStr);
            } catch (Exception e) {
                log.warn("Failed to parse entry time for user {}: {}", userId, e.getMessage());
            }
        }
        return null;
    }

    public boolean isUserEligibleForMetrics(Long experimentId, String userId, long delayMinutes) {
        LocalDateTime entryTime = getUserEntryTime(experimentId, userId);
        if (entryTime == null) {
            return false;
        }
        LocalDateTime eligibleTime = entryTime.plusMinutes(delayMinutes);
        return LocalDateTime.now().isAfter(eligibleTime);
    }

    public void clearBucketCache(Long experimentId) {
        String pattern = BUCKET_CACHE_PREFIX + experimentId + ":*";
        try {
            redisTemplate.delete(redisTemplate.keys(pattern));
        } catch (Exception e) {
            log.warn("清除实验缓存失败: {}", experimentId, e);
        }
        experimentHashRings.remove(experimentId);
    }
}
