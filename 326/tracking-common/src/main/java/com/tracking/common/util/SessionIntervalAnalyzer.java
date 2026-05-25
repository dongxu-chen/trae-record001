package com.tracking.common.util;

import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.UserSessionStats;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class SessionIntervalAnalyzer {

    private static final Logger LOG = LoggerFactory.getLogger(SessionIntervalAnalyzer.class);

    public static UserSessionStats analyzeSessionIntervals(List<Long> sessionEndTimes, 
                                                           String userId, String anonymousId,
                                                           String platform, String appId) {
        if (sessionEndTimes == null || sessionEndTimes.size() < 2) {
            return createDefaultStats(userId, anonymousId, platform, appId);
        }

        List<Long> sortedTimes = new ArrayList<>(sessionEndTimes);
        Collections.sort(sortedTimes);

        List<Long> intervals = new ArrayList<>();
        for (int i = 1; i < sortedTimes.size(); i++) {
            long interval = sortedTimes.get(i) - sortedTimes.get(i - 1);
            if (interval > 0 && interval < TrackingConstants.SESSION_TIMEOUT_MAX_MILLIS * 10) {
                intervals.add(interval);
            }
        }

        if (intervals.size() < TrackingConstants.SESSION_STATS_MIN_SAMPLES) {
            return createDefaultStats(userId, anonymousId, platform, appId);
        }

        Collections.sort(intervals);

        long avgInterval = calculateAverage(intervals);
        long medianInterval = calculatePercentile(intervals, 50);
        long p75Interval = calculatePercentile(intervals, 75);
        long p90Interval = calculatePercentile(intervals, 90);
        long p95Interval = calculatePercentile(intervals, 95);
        long minInterval = intervals.get(0);
        long maxInterval = intervals.get(intervals.size() - 1);

        long dynamicTimeout = calculateDynamicSessionTimeout(
            avgInterval, medianInterval, p75Interval, p90Interval, intervals.size());

        return UserSessionStats.builder()
                .userId(userId)
                .anonymousId(anonymousId)
                .totalSessions(sortedTimes.size())
                .avgSessionInterval(avgInterval)
                .medianSessionInterval(medianInterval)
                .p75SessionInterval(p75Interval)
                .p90SessionInterval(p90Interval)
                .p95SessionInterval(p95Interval)
                .minSessionInterval(minInterval)
                .maxSessionInterval(maxInterval)
                .sessionIntervals(intervals)
                .dynamicSessionTimeout(dynamicTimeout)
                .sampleSize(intervals.size())
                .lastUpdateTime(System.currentTimeMillis())
                .platform(platform)
                .appId(appId)
                .build();
    }

    public static long calculateDynamicSessionTimeout(long avg, long median, 
                                                      long p75, long p90, int sampleSize) {
        double weightMedian = 0.4;
        double weightP75 = 0.3;
        double weightP90 = 0.2;
        double weightAvg = 0.1;

        double sampleFactor = Math.min(1.0, (double) sampleSize / 100.0);

        long baseTimeout = (long) (
            median * weightMedian +
            p75 * weightP75 +
            p90 * weightP90 +
            avg * weightAvg
        );

        long varianceFactor = (p90 - median) / 2;
        baseTimeout += varianceFactor * sampleFactor;

        baseTimeout = Math.min(baseTimeout, TrackingConstants.SESSION_TIMEOUT_MAX_MILLIS);
        baseTimeout = Math.max(baseTimeout, TrackingConstants.SESSION_TIMEOUT_MIN_MILLIS);

        baseTimeout = Math.round(baseTimeout / 60000.0) * 60000;

        return baseTimeout;
    }

    private static long calculateAverage(List<Long> values) {
        if (values == null || values.isEmpty()) return 0;
        long sum = 0;
        for (long value : values) {
            sum += value;
        }
        return sum / values.size();
    }

    public static long calculatePercentile(List<Long> sortedValues, double percentile) {
        if (sortedValues == null || sortedValues.isEmpty()) {
            return 0;
        }

        int index = (int) Math.ceil(percentile / 100.0 * sortedValues.size()) - 1;
        index = Math.max(0, Math.min(index, sortedValues.size() - 1));

        return sortedValues.get(index);
    }

    private static UserSessionStats createDefaultStats(String userId, String anonymousId,
                                                       String platform, String appId) {
        return UserSessionStats.builder()
                .userId(userId)
                .anonymousId(anonymousId)
                .totalSessions(0)
                .avgSessionInterval(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .medianSessionInterval(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .p75SessionInterval(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .p90SessionInterval(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .p95SessionInterval(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .minSessionInterval(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .maxSessionInterval(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .dynamicSessionTimeout(TrackingConstants.SESSION_TIMEOUT_MILLIS)
                .sampleSize(0)
                .lastUpdateTime(System.currentTimeMillis())
                .platform(platform)
                .appId(appId)
                .build();
    }

    public static UserSessionStats mergeUserSessionStats(UserSessionStats existing, 
                                                          List<Long> newSessionEndTimes) {
        if (existing == null) {
            return null;
        }

        List<Long> allTimes = new ArrayList<>();
        if (existing.getSessionIntervals() != null) {
            long lastTime = 0;
            for (Long interval : existing.getSessionIntervals()) {
                lastTime += interval;
                allTimes.add(lastTime);
            }
        }
        if (newSessionEndTimes != null) {
            allTimes.addAll(newSessionEndTimes);
        }

        return analyzeSessionIntervals(allTimes, existing.getUserId(), 
            existing.getAnonymousId(), existing.getPlatform(), existing.getAppId());
    }
}
