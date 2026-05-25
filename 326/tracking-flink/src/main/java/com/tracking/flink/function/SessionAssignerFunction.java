package com.tracking.flink.function;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.SessionInfo;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.model.UserSessionStats;
import com.tracking.common.util.IdGenerator;
import com.tracking.common.util.SessionIntervalAnalyzer;
import org.apache.flink.api.common.state.ListState;
import org.apache.flink.api.common.state.ListStateDescriptor;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.apache.flink.util.OutputTag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.util.ArrayList;
import java.util.List;

public class SessionAssignerFunction extends KeyedProcessFunction<String, TrackEvent, TrackEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(SessionAssignerFunction.class);

    private static final long STATS_UPDATE_INTERVAL_MS = 10 * 60 * 1000L;
    private static final int MAX_SESSION_HISTORY = 100;

    public static final OutputTag<UserSessionStats> SESSION_STATS_TAG = 
        new OutputTag<UserSessionStats>("session-stats") {};

    private final String redisHost;
    private final int redisPort;
    private final String redisPassword;
    private final long defaultSessionTimeout;

    private transient ValueState<SessionInfo> sessionState;
    private transient ValueState<UserSessionStats> userStatsState;
    private transient ValueState<Long> lastStatsUpdateTimeState;
    private transient ListState<Long> sessionEndTimesState;
    private transient JedisPool jedisPool;

    public SessionAssignerFunction(String redisHost, int redisPort, String redisPassword, long sessionTimeout) {
        this.redisHost = redisHost;
        this.redisPort = redisPort;
        this.redisPassword = redisPassword;
        this.defaultSessionTimeout = sessionTimeout;
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<SessionInfo> sessionDescriptor = new ValueStateDescriptor<>(
                "session-state",
                org.apache.flink.api.common.typeinfo.TypeInformation.of(SessionInfo.class)
        );
        sessionState = getRuntimeContext().getState(sessionDescriptor);

        ValueStateDescriptor<UserSessionStats> statsDescriptor = new ValueStateDescriptor<>(
                "user-session-stats",
                org.apache.flink.api.common.typeinfo.TypeInformation.of(UserSessionStats.class)
        );
        userStatsState = getRuntimeContext().getState(statsDescriptor);

        ValueStateDescriptor<Long> lastUpdateDescriptor = new ValueStateDescriptor<>(
                "last-stats-update-time",
                Long.class
        );
        lastStatsUpdateTimeState = getRuntimeContext().getState(lastUpdateDescriptor);

        ListStateDescriptor<Long> sessionTimesDescriptor = new ListStateDescriptor<>(
                "session-end-times",
                Long.class
        );
        sessionEndTimesState = getRuntimeContext().getListState(sessionTimesDescriptor);

        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(128);
        poolConfig.setMaxIdle(64);
        poolConfig.setMinIdle(16);
        if (redisPassword != null && !redisPassword.isEmpty()) {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000, redisPassword);
        } else {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000);
        }
    }

    @Override
    public void processElement(TrackEvent event, Context context, Collector<TrackEvent> collector) throws Exception {
        SessionInfo currentSession = sessionState.value();
        long currentTime = context.timerService().currentProcessingTime();

        long dynamicTimeout = getDynamicSessionTimeout(event);
        event.addProperty("session_timeout_minutes", dynamicTimeout / 60000);

        if (currentSession == null) {
            currentSession = SessionInfo.create(event);
            event.addProperty("session_new", true);
            event.addProperty("session_start_time", currentSession.getStartTime());
            event.addProperty("session_dynamic_timeout", dynamicTimeout);
        } else if (currentSession.isExpired(currentTime, dynamicTimeout)) {
            SessionInfo expiredSession = currentSession;
            expiredSession.setEndTime(currentTime);

            updateSessionHistory(expiredSession.getEndTime());

            TrackEvent sessionEndEvent = createSessionEndEvent(expiredSession, event, dynamicTimeout);
            collector.collect(sessionEndEvent);

            currentSession = SessionInfo.create(event);
            event.addProperty("session_new", true);
            event.addProperty("session_start_time", currentSession.getStartTime());
            event.addProperty("session_dynamic_timeout", dynamicTimeout);

            maybeUpdateUserStats(event, currentTime, context);
        } else {
            currentSession.update(event);
            event.addProperty("session_new", false);
            event.addProperty("session_start_time", currentSession.getStartTime());
            event.addProperty("session_event_index", currentSession.getEventCount());
            event.addProperty("session_dynamic_timeout", dynamicTimeout);
        }

        sessionState.update(currentSession);

        saveSessionToRedis(currentSession);

        context.timerService().registerProcessingTimeTimer(currentSession.getLastEventTime() + dynamicTimeout);

        collector.collect(event);
    }

    @Override
    public void onTimer(long timestamp, OnTimerContext ctx, Collector<TrackEvent> out) throws Exception {
        SessionInfo session = sessionState.value();
        if (session != null) {
            long dynamicTimeout = getDynamicSessionTimeoutFromState();
            if (session.isExpired(timestamp, dynamicTimeout)) {
                session.setEndTime(timestamp);
                updateSessionHistory(session.getEndTime());

                TrackEvent sessionEndEvent = createSessionEndEvent(session, null, dynamicTimeout);
                out.collect(sessionEndEvent);

                sessionState.clear();
                deleteSessionFromRedis(session.getSessionId());

                maybeUpdateUserStats(null, timestamp, ctx);
            } else {
                ctx.timerService().registerProcessingTimeTimer(session.getLastEventTime() + dynamicTimeout);
            }
        }
    }

    private long getDynamicSessionTimeout(TrackEvent event) {
        try {
            UserSessionStats stats = userStatsState.value();
            if (stats != null && stats.getDynamicSessionTimeout() != null 
                && stats.getSampleSize() >= TrackingConstants.SESSION_STATS_MIN_SAMPLES) {
                return stats.getDynamicSessionTimeout();
            }

            UserSessionStats redisStats = getUserStatsFromRedis(event);
            if (redisStats != null && redisStats.getDynamicSessionTimeout() != null
                && redisStats.getSampleSize() >= TrackingConstants.SESSION_STATS_MIN_SAMPLES) {
                userStatsState.update(redisStats);
                return redisStats.getDynamicSessionTimeout();
            }
        } catch (Exception e) {
            LOG.warn("Failed to get dynamic session timeout", e);
        }
        return defaultSessionTimeout;
    }

    private long getDynamicSessionTimeoutFromState() {
        try {
            UserSessionStats stats = userStatsState.value();
            if (stats != null && stats.getDynamicSessionTimeout() != null) {
                return stats.getDynamicSessionTimeout();
            }
        } catch (Exception e) {
            LOG.warn("Failed to get dynamic session timeout from state", e);
        }
        return defaultSessionTimeout;
    }

    private UserSessionStats getUserStatsFromRedis(TrackEvent event) {
        if (event.getUserId() == null && event.getAnonymousId() == null) {
            return null;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = event.getUserId() != null 
                ? TrackingConstants.REDIS_KEY_USER_SESSION_STATS + event.getUserId()
                : TrackingConstants.REDIS_KEY_USER_SESSION_STATS + event.getAnonymousId();

            String statsJson = jedis.get(key);
            if (statsJson != null) {
                return JSON.parseObject(statsJson, UserSessionStats.class);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get user stats from Redis", e);
        }
        return null;
    }

    private void updateSessionHistory(Long sessionEndTime) throws Exception {
        if (sessionEndTime == null) return;

        List<Long> allTimes = new ArrayList<>();
        for (Long time : sessionEndTimesState.get()) {
            allTimes.add(time);
        }

        allTimes.add(sessionEndTime);

        if (allTimes.size() > MAX_SESSION_HISTORY) {
            allTimes = new ArrayList<>(allTimes.subList(allTimes.size() - MAX_SESSION_HISTORY, allTimes.size()));
        }

        sessionEndTimesState.clear();
        for (Long time : allTimes) {
            sessionEndTimesState.add(time);
        }
    }

    private void maybeUpdateUserStats(TrackEvent event, long currentTime, Context context) throws Exception {
        Long lastUpdateTime = lastStatsUpdateTimeState.value();
        if (lastUpdateTime != null && (currentTime - lastUpdateTime) < STATS_UPDATE_INTERVAL_MS) {
            return;
        }

        List<Long> sessionEndTimes = new ArrayList<>();
        for (Long time : sessionEndTimesState.get()) {
            sessionEndTimes.add(time);
        }

        if (sessionEndTimes.size() < 2) {
            return;
        }

        String userId = null;
        String anonymousId = null;
        String platform = null;
        String appId = null;

        if (event != null) {
            userId = event.getUserId();
            anonymousId = event.getAnonymousId();
            platform = event.getPlatform();
            appId = event.getAppId();
        } else {
            UserSessionStats existing = userStatsState.value();
            if (existing != null) {
                userId = existing.getUserId();
                anonymousId = existing.getAnonymousId();
                platform = existing.getPlatform();
                appId = existing.getAppId();
            }
        }

        UserSessionStats newStats = SessionIntervalAnalyzer.analyzeSessionIntervals(
            sessionEndTimes, userId, anonymousId, platform, appId);

        userStatsState.update(newStats);
        lastStatsUpdateTimeState.update(currentTime);

        saveUserStatsToRedis(newStats);

        if (context != null && newStats.getSampleSize() >= TrackingConstants.SESSION_STATS_MIN_SAMPLES) {
            context.output(SESSION_STATS_TAG, newStats);
        }

        LOG.debug("Updated user session stats: user={}, timeout={}min, samples={}",
            userId != null ? userId : anonymousId,
            newStats.getDynamicSessionTimeout() / 60000,
            newStats.getSampleSize());
    }

    private void saveUserStatsToRedis(UserSessionStats stats) {
        if (stats == null) return;

        try (Jedis jedis = jedisPool.getResource()) {
            String key = stats.getUserId() != null
                ? TrackingConstants.REDIS_KEY_USER_SESSION_STATS + stats.getUserId()
                : TrackingConstants.REDIS_KEY_USER_SESSION_STATS + stats.getAnonymousId();

            if (key != null) {
                jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, JSON.toJSONString(stats));
            }
        } catch (Exception e) {
            LOG.warn("Failed to save user stats to Redis", e);
        }
    }

    private TrackEvent createSessionEndEvent(SessionInfo session, TrackEvent sourceEvent, long dynamicTimeout) {
        TrackEvent event = TrackEvent.builder()
                .id(IdGenerator.generateEventId())
                .event(TrackingConstants.EVENT_SESSION_END)
                .timestamp(session.getEndTime())
                .receiveTime(System.currentTimeMillis())
                .anonymousId(session.getAnonymousId())
                .userId(session.getUserId())
                .sessionId(session.getSessionId())
                .deviceId(session.getDeviceId())
                .source(TrackingConstants.SOURCE_SDK)
                .build();

        if (sourceEvent != null) {
            event.setPlatform(sourceEvent.getPlatform());
            event.setAppId(sourceEvent.getAppId());
            event.setAppVersion(sourceEvent.getAppVersion());
            event.setChannel(sourceEvent.getChannel());
            event.setOs(sourceEvent.getOs());
            event.setOsVersion(sourceEvent.getOsVersion());
            event.setIp(sourceEvent.getIp());
        }

        event.addProperty("session_duration", session.getEndTime() - session.getStartTime());
        event.addProperty("session_event_count", session.getEventCount());
        event.addProperty("session_start_time", session.getStartTime());
        event.addProperty("session_end_time", session.getEndTime());
        event.addProperty("session_first_page", session.getFirstPage());
        event.addProperty("session_last_page", session.getLastPage());
        event.addProperty("session_entry_source", session.getEntrySource());
        event.addProperty("session_dynamic_timeout", dynamicTimeout);
        event.addProperty("session_timeout_minutes", dynamicTimeout / 60000);

        return event;
    }

    private void saveSessionToRedis(SessionInfo session) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_SESSION + session.getSessionId();
            jedis.setex(key, TrackingConstants.REDIS_SESSION_EXPIRE_MINUTES * 60, JSON.toJSONString(session));
        } catch (Exception e) {
            LOG.warn("Failed to save session to Redis: {}", session.getSessionId(), e);
        }
    }

    private void deleteSessionFromRedis(String sessionId) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_SESSION + sessionId;
            jedis.del(key);
        } catch (Exception e) {
            LOG.warn("Failed to delete session from Redis: {}", sessionId, e);
        }
    }

    @Override
    public void close() {
        if (jedisPool != null) {
            jedisPool.close();
        }
    }
}
