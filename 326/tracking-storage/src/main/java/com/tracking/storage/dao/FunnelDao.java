package com.tracking.storage.dao;

import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.FunnelQuery;
import com.tracking.common.model.FunnelResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.TimeZone;

@Repository
public class FunnelDao {

    private static final Logger LOG = LoggerFactory.getLogger(FunnelDao.class);

    private final JdbcTemplate jdbcTemplate;

    public FunnelDao(DataSource dataSource) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
    }

    public FunnelResult calculateFunnel(FunnelQuery query) {
        List<String> events = query.getEvents();
        if (events == null || events.isEmpty()) {
            throw new IllegalArgumentException("Funnel events cannot be empty");
        }

        boolean useSlidingWindow = Boolean.TRUE.equals(query.getSlidingWindow());
        
        if (useSlidingWindow) {
            return calculateSlidingWindowFunnel(query);
        } else {
            return calculateSingleWindowFunnel(query);
        }
    }

    private FunnelResult calculateSingleWindowFunnel(FunnelQuery query) {
        List<String> events = query.getEvents();
        int windowMinutes = query.getWindowMinutes() != null ? query.getWindowMinutes() : 60;
        long windowMillis = windowMinutes * 60 * 1000L;

        List<FunnelResult.FunnelStep> steps = new ArrayList<>();
        long previousCount = 0;

        Long totalUsers = countUsersForEvent(events.get(0), query, query.getStartTime(), query.getEndTime());
        previousCount = totalUsers;

        for (int i = 0; i < events.size(); i++) {
            String currentEvent = events.get(i);
            long currentCount;

            if (i == 0) {
                currentCount = totalUsers;
            } else {
                String previousEvent = events.get(i - 1);
                currentCount = countUsersForFunnelStep(previousEvent, currentEvent, windowMillis, query, 
                    query.getStartTime(), query.getEndTime());
            }

            double conversionRate = previousCount > 0 ? (double) currentCount / previousCount * 100 : 0;
            double dropOffRate = 100 - conversionRate;

            FunnelResult.FunnelStep step = FunnelResult.FunnelStep.builder()
                    .stepIndex(i)
                    .eventName(currentEvent)
                    .userCount(currentCount)
                    .conversionRate(Math.round(conversionRate * 100) / 100.0)
                    .dropOffRate(Math.round(dropOffRate * 100) / 100.0)
                    .build();
            steps.add(step);

            previousCount = currentCount;
        }

        return FunnelResult.builder()
                .funnelName(query.getFunnelName())
                .steps(steps)
                .totalUsers(totalUsers)
                .startTime(query.getStartTime())
                .endTime(query.getEndTime())
                .slidingWindow(false)
                .build();
    }

    private FunnelResult calculateSlidingWindowFunnel(FunnelQuery query) {
        List<String> events = query.getEvents();
        int windowMinutes = query.getWindowMinutes() != null ? query.getWindowMinutes() : 60;
        long windowMillis = windowMinutes * 60 * 1000L;

        long startTime = query.getStartTime() != null ? query.getStartTime() : 
            System.currentTimeMillis() - 24 * 60 * 60 * 1000L;
        long endTime = query.getEndTime() != null ? query.getEndTime() : System.currentTimeMillis();

        long slidingWindowSizeMillis = calculateSlidingWindowSizeMillis(query);
        long slidingStepMillis = calculateSlidingStepMillis(query, slidingWindowSizeMillis);

        List<FunnelResult.SlidingWindowResult> slidingResults = new ArrayList<>();

        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        sdf.setTimeZone(TimeZone.getDefault());

        long windowStart = startTime;
        while (windowStart + slidingWindowSizeMillis <= endTime) {
            long windowEnd = windowStart + slidingWindowSizeMillis;

            List<FunnelResult.FunnelStep> windowSteps = new ArrayList<>();
            long windowPreviousCount = 0;

            Long windowTotalUsers = countUsersForEvent(events.get(0), query, windowStart, windowEnd);
            windowPreviousCount = windowTotalUsers;

            for (int i = 0; i < events.size(); i++) {
                String currentEvent = events.get(i);
                long currentCount;

                if (i == 0) {
                    currentCount = windowTotalUsers;
                } else {
                    String previousEvent = events.get(i - 1);
                    currentCount = countUsersForFunnelStep(previousEvent, currentEvent, windowMillis, 
                        query, windowStart, windowEnd);
                }

                double conversionRate = windowPreviousCount > 0 ? 
                    (double) currentCount / windowPreviousCount * 100 : 0;
                double dropOffRate = 100 - conversionRate;

                FunnelResult.FunnelStep step = FunnelResult.FunnelStep.builder()
                        .stepIndex(i)
                        .eventName(currentEvent)
                        .userCount(currentCount)
                        .conversionRate(Math.round(conversionRate * 100) / 100.0)
                        .dropOffRate(Math.round(dropOffRate * 100) / 100.0)
                        .build();
                windowSteps.add(step);

                windowPreviousCount = currentCount;
            }

            String windowLabel = generateWindowLabel(query.getSlidingWindowUnit(), windowStart, windowEnd, sdf);

            FunnelResult.SlidingWindowResult windowResult = FunnelResult.SlidingWindowResult.builder()
                    .windowStartTime(windowStart)
                    .windowEndTime(windowEnd)
                    .windowLabel(windowLabel)
                    .steps(windowSteps)
                    .totalUsers(windowTotalUsers)
                    .build();

            slidingResults.add(windowResult);

            windowStart += slidingStepMillis;
        }

        return FunnelResult.builder()
                .funnelName(query.getFunnelName())
                .startTime(startTime)
                .endTime(endTime)
                .slidingWindow(true)
                .slidingWindowUnit(query.getSlidingWindowUnit())
                .slidingWindowSize(query.getSlidingWindowSize())
                .slidingWindowResults(slidingResults)
                .build();
    }

    private long calculateSlidingWindowSizeMillis(FunnelQuery query) {
        String unit = query.getSlidingWindowUnit();
        int size = query.getSlidingWindowSize() != null ? query.getSlidingWindowSize() : 1;

        if (TrackingConstants.FUNNEL_WINDOW_HOURLY.equals(unit)) {
            return size * 60 * 60 * 1000L;
        } else if (TrackingConstants.FUNNEL_WINDOW_DAILY.equals(unit)) {
            return size * 24 * 60 * 60 * 1000L;
        } else if (TrackingConstants.FUNNEL_WINDOW_WEEKLY.equals(unit)) {
            return size * 7 * 24 * 60 * 60 * 1000L;
        } else {
            return (query.getSlidingWindowSize() != null ? 
                query.getSlidingWindowSize() : 60) * 60 * 1000L;
        }
    }

    private long calculateSlidingStepMillis(FunnelQuery query, long windowSize) {
        if (query.getSlidingWindowStep() != null && query.getSlidingWindowStep() > 0) {
            String unit = query.getSlidingWindowUnit();
            if (TrackingConstants.FUNNEL_WINDOW_HOURLY.equals(unit)) {
                return query.getSlidingWindowStep() * 60 * 60 * 1000L;
            } else if (TrackingConstants.FUNNEL_WINDOW_DAILY.equals(unit)) {
                return query.getSlidingWindowStep() * 24 * 60 * 60 * 1000L;
            } else if (TrackingConstants.FUNNEL_WINDOW_WEEKLY.equals(unit)) {
                return query.getSlidingWindowStep() * 7 * 24 * 60 * 60 * 1000L;
            } else {
                return query.getSlidingWindowStep() * 60 * 1000L;
            }
        }
        return windowSize;
    }

    private String generateWindowLabel(String unit, long windowStart, long windowEnd, SimpleDateFormat sdf) {
        SimpleDateFormat dayFormat = new SimpleDateFormat("MM-dd");
        SimpleDateFormat hourFormat = new SimpleDateFormat("HH:mm");

        if (TrackingConstants.FUNNEL_WINDOW_HOURLY.equals(unit)) {
            return hourFormat.format(new Date(windowStart)) + "-" + hourFormat.format(new Date(windowEnd));
        } else if (TrackingConstants.FUNNEL_WINDOW_DAILY.equals(unit)) {
            return dayFormat.format(new Date(windowStart));
        } else if (TrackingConstants.FUNNEL_WINDOW_WEEKLY.equals(unit)) {
            return dayFormat.format(new Date(windowStart)) + " ~ " + dayFormat.format(new Date(windowEnd));
        } else {
            return sdf.format(new Date(windowStart));
        }
    }

    private Long countUsersForEvent(String event, FunnelQuery query, Long windowStart, Long windowEnd) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT uniqExact(user_id) FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
                .append(" WHERE event = ? ");
        params.add(event);

        if (windowStart != null) {
            sql.append("AND timestamp >= ? ");
            params.add(windowStart);
        }
        if (windowEnd != null) {
            sql.append("AND timestamp <= ? ");
            params.add(windowEnd);
        }
        if (query.getPlatform() != null) {
            sql.append("AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("AND app_id = ? ");
            params.add(query.getAppId());
        }
        if (query.getChannel() != null) {
            sql.append("AND channel = ? ");
            params.add(query.getChannel());
        }

        sql.append("AND user_id != '' AND user_id IS NOT NULL");

        LOG.debug("Count users SQL: {}, params: {}", sql, params);
        Long result = jdbcTemplate.queryForObject(sql.toString(), params.toArray(), Long.class);
        return result != null ? result : 0L;
    }

    private Long countUsersForFunnelStep(String fromEvent, String toEvent, long windowMillis, 
                                          FunnelQuery query, Long windowStart, Long windowEnd) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT count(DISTINCT t1.user_id) FROM (");
        sql.append("SELECT user_id, min(timestamp) as first_time ");
        sql.append("FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS).append(" ");
        sql.append("WHERE event = ? ");
        params.add(fromEvent);
        if (windowStart != null) {
            sql.append("AND timestamp >= ? ");
            params.add(windowStart);
        }
        if (windowEnd != null) {
            sql.append("AND timestamp <= ? ");
            params.add(windowEnd);
        }
        if (query.getPlatform() != null) {
            sql.append("AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("AND app_id = ? ");
            params.add(query.getAppId());
        }
        sql.append("AND user_id != '' AND user_id IS NOT NULL ");
        sql.append("GROUP BY user_id) t1 ");
        sql.append("INNER JOIN (");
        sql.append("SELECT user_id, timestamp as next_time ");
        sql.append("FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS).append(" ");
        sql.append("WHERE event = ? ");
        params.add(toEvent);
        if (windowStart != null) {
            sql.append("AND timestamp >= ? ");
            params.add(windowStart);
        }
        if (windowEnd != null) {
            sql.append("AND timestamp <= ? ");
            params.add(windowEnd);
        }
        if (query.getPlatform() != null) {
            sql.append("AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("AND app_id = ? ");
            params.add(query.getAppId());
        }
        sql.append("AND user_id != '' AND user_id IS NOT NULL) t2 ");
        sql.append("ON t1.user_id = t2.user_id ");
        sql.append("WHERE t2.next_time >= t1.first_time AND t2.next_time <= t1.first_time + ? ");
        params.add(windowMillis);

        LOG.debug("Funnel step SQL: {}, params: {}", sql, params);
        Long result = jdbcTemplate.queryForObject(sql.toString(), params.toArray(), Long.class);
        return result != null ? result : 0L;
    }
}
