package com.replay.detector.service;

import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.model.AdaptiveThresholdState;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

@Slf4j
@Service
@RequiredArgsConstructor
public class AdaptiveThresholdService {

    private static final String QPS_COUNTER_PREFIX = "replay:qps:";
    private static final String QPS_WINDOW_KEY = "replay:adaptive:qps:window";
    private static final String STATE_KEY = "replay:adaptive:state";

    private final StringRedisTemplate redisTemplate;
    private final ReplayDetectionProperties properties;

    private final AtomicReference<AdaptiveThresholdState> cachedState = new AtomicReference<>();

    public void recordRequest() {
        if (!properties.getAdaptive().isEnabled()) {
            return;
        }

        long now = System.currentTimeMillis();
        String secondBucket = QPS_COUNTER_PREFIX + (now / 1000);
        redisTemplate.opsForValue().increment(secondBucket);
        redisTemplate.expire(secondBucket, 10, TimeUnit.SECONDS);

        redisTemplate.opsForList().rightPush(QPS_WINDOW_KEY, String.valueOf(now));
        redisTemplate.opsForList().trim(QPS_WINDOW_KEY, -600, -1);
        redisTemplate.expire(QPS_WINDOW_KEY, 600, TimeUnit.SECONDS);
    }

    public int getAdaptiveMaxReplayCount() {
        if (!properties.getAdaptive().isEnabled()) {
            return properties.getMaxReplayCount();
        }

        AdaptiveThresholdState state = getCachedState();
        return state.getAdjustedMaxReplayCount();
    }

    public AdaptiveThresholdState getCurrentState() {
        return computeState();
    }

    public AdaptiveThresholdState refreshState() {
        AdaptiveThresholdState state = computeState();
        cachedState.set(state);
        persistState(state);
        return state;
    }

    private AdaptiveThresholdState getCachedState() {
        AdaptiveThresholdState state = cachedState.get();
        if (state != null && (System.currentTimeMillis() - state.getLastUpdatedAt()) < properties.getAdaptive().getRefreshIntervalMs()) {
            return state;
        }

        state = loadPersistedState();
        if (state != null && (System.currentTimeMillis() - state.getLastUpdatedAt()) < properties.getAdaptive().getRefreshIntervalMs()) {
            cachedState.set(state);
            return state;
        }

        state = computeState();
        cachedState.set(state);
        persistState(state);
        return state;
    }

    private AdaptiveThresholdState computeState() {
        double currentQps = measureCurrentQps();
        double baselineQps = properties.getAdaptive().getBaselineQps();
        int original = properties.getMaxReplayCount();

        double ratio = baselineQps > 0 ? currentQps / baselineQps : 1.0;
        double multiplier;
        int adjusted;
        String reason;

        if (ratio > properties.getAdaptive().getHighLoadRatio()) {
            multiplier = properties.getAdaptive().getHighLoadSensitivity();
            adjusted = (int) Math.ceil(original * multiplier);
            reason = String.format("High QPS detected: current=%.1f, baseline=%.1f, ratio=%.2f, easing threshold",
                    currentQps, baselineQps, ratio);
        } else if (ratio < (1.0 / properties.getAdaptive().getHighLoadRatio())) {
            multiplier = properties.getAdaptive().getLowLoadSensitivity();
            adjusted = (int) Math.ceil(original * multiplier);
            reason = String.format("Low QPS detected: current=%.1f, baseline=%.1f, ratio=%.2f, tightening threshold",
                    currentQps, baselineQps, ratio);
        } else {
            multiplier = 1.0;
            adjusted = original;
            reason = String.format("Normal QPS: current=%.1f, baseline=%.1f, ratio=%.2f, default threshold",
                    currentQps, baselineQps, ratio);
        }

        int minCount = properties.getAdaptive().getMinReplayCount();
        int maxCount = properties.getAdaptive().getMaxReplayCount();
        adjusted = Math.max(minCount, Math.min(maxCount, adjusted));

        log.debug("Adaptive threshold: qps={}, baseline={}, original={}, adjusted={}, multiplier={}",
                String.format("%.1f", currentQps), String.format("%.1f", baselineQps), original, adjusted, String.format("%.2f", multiplier));

        return AdaptiveThresholdState.builder()
                .currentQps(currentQps)
                .baselineQps(baselineQps)
                .adjustedMaxReplayCount(adjusted)
                .originalMaxReplayCount(original)
                .sensitivityMultiplier(multiplier)
                .lastUpdatedAt(System.currentTimeMillis())
                .adjustmentReason(reason)
                .adaptiveEnabled(properties.getAdaptive().isEnabled())
                .build();
    }

    private double measureCurrentQps() {
        long now = System.currentTimeMillis();
        int windowSeconds = properties.getAdaptive().getQpsWindowSeconds();
        long windowStart = now - windowSeconds * 1000L;

        long totalRequests = 0;
        for (long bucket = windowStart / 1000; bucket <= now / 1000; bucket++) {
            String key = QPS_COUNTER_PREFIX + bucket;
            String val = redisTemplate.opsForValue().get(key);
            if (val != null) {
                totalRequests += Long.parseLong(val);
            }
        }

        return (double) totalRequests / windowSeconds;
    }

    private void persistState(AdaptiveThresholdState state) {
        try {
            String stateStr = String.join("|",
                    String.valueOf(state.getCurrentQps()),
                    String.valueOf(state.getBaselineQps()),
                    String.valueOf(state.getAdjustedMaxReplayCount()),
                    String.valueOf(state.getOriginalMaxReplayCount()),
                    String.valueOf(state.getSensitivityMultiplier()),
                    String.valueOf(state.getLastUpdatedAt()),
                    state.getAdjustmentReason(),
                    String.valueOf(state.isAdaptiveEnabled())
            );
            redisTemplate.opsForValue().set(STATE_KEY, stateStr, 5, TimeUnit.MINUTES);
        } catch (Exception e) {
            log.error("Failed to persist adaptive threshold state", e);
        }
    }

    private AdaptiveThresholdState loadPersistedState() {
        try {
            String stateStr = redisTemplate.opsForValue().get(STATE_KEY);
            if (stateStr == null) return null;

            String[] parts = stateStr.split("\\|", -1);
            if (parts.length < 8) return null;

            return AdaptiveThresholdState.builder()
                    .currentQps(Double.parseDouble(parts[0]))
                    .baselineQps(Double.parseDouble(parts[1]))
                    .adjustedMaxReplayCount(Integer.parseInt(parts[2]))
                    .originalMaxReplayCount(Integer.parseInt(parts[3]))
                    .sensitivityMultiplier(Double.parseDouble(parts[4]))
                    .lastUpdatedAt(Long.parseLong(parts[5]))
                    .adjustmentReason(parts[6])
                    .adaptiveEnabled(Boolean.parseBoolean(parts[7]))
                    .build();
        } catch (Exception e) {
            log.debug("Failed to load persisted adaptive state", e);
            return null;
        }
    }
}
