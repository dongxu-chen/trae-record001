package com.sessionguard.store;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.sessionguard.model.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Repository;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Repository
public class SessionStore {

    private static final String SESSION_PREFIX = "sg:session:";
    private static final String USER_SESSIONS_PREFIX = "sg:user:";
    private static final String RISK_PREFIX = "sg:risk:";
    private static final String EVENT_PREFIX = "sg:event:";
    private static final String IP_HISTORY_PREFIX = "sg:ip_history:";
    private static final String FP_HISTORY_PREFIX = "sg:fp_history:";
    private static final String BASELINE_PREFIX = "sg:baseline:";
    private static final String THREAT_INTEL_PREFIX = "sg:threat:";
    private static final String LOCATION_JUMP_PREFIX = "sg:loc_jump:";
    private static final String USER_LOCATION_HISTORY = "sg:user_loc:";

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    public SessionStore(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
    }

    public void saveSession(SessionProfile profile, long ttlMinutes) {
        try {
            String json = objectMapper.writeValueAsString(profile);
            String key = SESSION_PREFIX + profile.getSessionId();
            redisTemplate.opsForValue().set(key, json, Duration.ofMinutes(ttlMinutes));

            String userKey = USER_SESSIONS_PREFIX + profile.getUserId();
            redisTemplate.opsForSet().add(userKey, profile.getSessionId());
            redisTemplate.expire(userKey, Duration.ofMinutes(ttlMinutes + 30));

            log.debug("Saved session {} for user {}", profile.getSessionId(), profile.getUserId());
        } catch (Exception e) {
            log.error("Failed to save session {}", profile.getSessionId(), e);
        }
    }

    public Optional<SessionProfile> getSession(String sessionId) {
        try {
            String json = redisTemplate.opsForValue().get(SESSION_PREFIX + sessionId);
            if (json == null) {
                return Optional.empty();
            }
            return Optional.of(objectMapper.readValue(json, SessionProfile.class));
        } catch (Exception e) {
            log.error("Failed to get session {}", sessionId, e);
            return Optional.empty();
        }
    }

    public List<SessionProfile> getSessionsByUser(String userId) {
        Set<String> sessionIds = redisTemplate.opsForSet().members(USER_SESSIONS_PREFIX + userId);
        if (sessionIds == null || sessionIds.isEmpty()) {
            return Collections.emptyList();
        }

        return sessionIds.stream()
                .map(this::getSession)
                .filter(Optional::isPresent)
                .map(Optional::get)
                .filter(SessionProfile::isActive)
                .collect(Collectors.toList());
    }

    public void invalidateSession(String sessionId, String reason) {
        getSession(sessionId).ifPresent(profile -> {
            profile.setActive(false);
            profile.setInvalidated(true);
            profile.setInvalidationReason(reason);
            saveSession(profile, 60);
            log.info("Session {} invalidated: {}", sessionId, reason);
        });
    }

    public void invalidateAllUserSessions(String userId, String reason) {
        List<SessionProfile> sessions = getSessionsByUser(userId);
        for (SessionProfile session : sessions) {
            invalidateSession(session.getSessionId(), reason);
        }
        log.info("All sessions for user {} invalidated: {}", userId, reason);
    }

    public int getActiveSessionCount(String userId) {
        return getSessionsByUser(userId).size();
    }

    public void saveRiskAssessment(RiskAssessment assessment, long ttlMinutes) {
        try {
            String json = objectMapper.writeValueAsString(assessment);
            redisTemplate.opsForValue().set(RISK_PREFIX + assessment.getSessionId(), json, Duration.ofMinutes(ttlMinutes));
        } catch (Exception e) {
            log.error("Failed to save risk assessment for session {}", assessment.getSessionId(), e);
        }
    }

    public Optional<RiskAssessment> getLatestRiskAssessment(String sessionId) {
        try {
            String json = redisTemplate.opsForValue().get(RISK_PREFIX + sessionId);
            if (json == null) {
                return Optional.empty();
            }
            return Optional.of(objectMapper.readValue(json, RiskAssessment.class));
        } catch (Exception e) {
            log.error("Failed to get risk assessment for session {}", sessionId, e);
            return Optional.empty();
        }
    }

    public void logEvent(SessionEvent event) {
        try {
            String json = objectMapper.writeValueAsString(event);
            String key = EVENT_PREFIX + event.getSessionId();
            redisTemplate.opsForList().rightPush(key, json);
            redisTemplate.expire(key, Duration.ofDays(7));
        } catch (Exception e) {
            log.error("Failed to log event for session {}", event.getSessionId(), e);
        }
    }

    public List<SessionEvent> getEventHistory(String sessionId) {
        try {
            List<String> events = redisTemplate.opsForList().range(EVENT_PREFIX + sessionId, 0, -1);
            if (events == null) {
                return Collections.emptyList();
            }
            List<SessionEvent> result = new ArrayList<>();
            for (String json : events) {
                result.add(objectMapper.readValue(json, SessionEvent.class));
            }
            return result;
        } catch (Exception e) {
            log.error("Failed to get event history for session {}", sessionId, e);
            return Collections.emptyList();
        }
    }

    public void saveIpHistory(String userId, String ipAddress) {
        String key = IP_HISTORY_PREFIX + userId;
        redisTemplate.opsForList().rightPush(key, ipAddress + "|" + LocalDateTime.now());
        redisTemplate.opsForList().trim(key, -50, -1);
        redisTemplate.expire(key, Duration.ofDays(30));
    }

    public List<String> getIpHistory(String userId, int limit) {
        List<String> raw = redisTemplate.opsForList().range(IP_HISTORY_PREFIX + userId, -limit, -1);
        return raw != null ? raw : Collections.emptyList();
    }

    public void saveFingerprintHistory(String userId, String fingerprintHash) {
        String key = FP_HISTORY_PREFIX + userId;
        redisTemplate.opsForList().rightPush(key, fingerprintHash + "|" + LocalDateTime.now());
        redisTemplate.opsForList().trim(key, -20, -1);
        redisTemplate.expire(key, Duration.ofDays(30));
    }

    public List<String> getFingerprintHistory(String userId, int limit) {
        List<String> raw = redisTemplate.opsForList().range(FP_HISTORY_PREFIX + userId, -limit, -1);
        return raw != null ? raw : Collections.emptyList();
    }

    public boolean isSessionActive(String sessionId) {
        return getSession(sessionId).map(SessionProfile::isActive).orElse(false);
    }

    public void deleteSession(String sessionId) {
        redisTemplate.delete(SESSION_PREFIX + sessionId);
        redisTemplate.delete(RISK_PREFIX + sessionId);
        redisTemplate.delete(EVENT_PREFIX + sessionId);
    }

    public void saveBehaviorBaseline(UserBehaviorBaseline baseline) {
        try {
            baseline.setLastUpdatedAt(LocalDateTime.now());
            String json = objectMapper.writeValueAsString(baseline);
            redisTemplate.opsForValue().set(BASELINE_PREFIX + baseline.getUserId(), json, Duration.ofDays(90));
            log.debug("Saved behavior baseline for user {}", baseline.getUserId());
        } catch (Exception e) {
            log.error("Failed to save behavior baseline for user {}", baseline.getUserId(), e);
        }
    }

    public Optional<UserBehaviorBaseline> getBehaviorBaseline(String userId) {
        try {
            String json = redisTemplate.opsForValue().get(BASELINE_PREFIX + userId);
            if (json == null) {
                return Optional.empty();
            }
            return Optional.of(objectMapper.readValue(json, UserBehaviorBaseline.class));
        } catch (Exception e) {
            log.error("Failed to get behavior baseline for user {}", userId, e);
            return Optional.empty();
        }
    }

    public void saveUserLocation(String userId, String country, String region, String city, String ip) {
        String key = USER_LOCATION_HISTORY + userId;
        String entry = country + "|" + region + "|" + city + "|" + ip + "|" + LocalDateTime.now();
        redisTemplate.opsForList().rightPush(key, entry);
        redisTemplate.opsForList().trim(key, -20, -1);
        redisTemplate.expire(key, Duration.ofDays(30));
    }

    public List<Map<String, Object>> getUserLocationHistory(String userId, int limit) {
        List<String> raw = redisTemplate.opsForList().range(USER_LOCATION_HISTORY + userId, -limit, -1);
        if (raw == null) return Collections.emptyList();

        List<Map<String, Object>> result = new ArrayList<>();
        for (String entry : raw) {
            String[] parts = entry.split("\\|");
            if (parts.length >= 4) {
                Map<String, Object> loc = new HashMap<>();
                loc.put("country", parts[0]);
                loc.put("region", parts[1]);
                loc.put("city", parts[2]);
                loc.put("ip", parts[3]);
                if (parts.length >= 5) {
                    loc.put("timestamp", parts[4]);
                }
                result.add(loc);
            }
        }
        return result;
    }

    public void saveLocationJumpDetection(LocationJumpDetection detection) {
        try {
            String json = objectMapper.writeValueAsString(detection);
            String key = LOCATION_JUMP_PREFIX + detection.getUserId();
            redisTemplate.opsForList().rightPush(key, json);
            redisTemplate.opsForList().trim(key, -10, -1);
            redisTemplate.expire(key, Duration.ofDays(30));
        } catch (Exception e) {
            log.error("Failed to save location jump detection", e);
        }
    }

    public List<LocationJumpDetection> getLocationJumpHistory(String userId) {
        try {
            List<String> raw = redisTemplate.opsForList().range(LOCATION_JUMP_PREFIX + userId, 0, -1);
            if (raw == null) return Collections.emptyList();
            List<LocationJumpDetection> result = new ArrayList<>();
            for (String json : raw) {
                result.add(objectMapper.readValue(json, LocationJumpDetection.class));
            }
            return result;
        } catch (Exception e) {
            log.error("Failed to get location jump history for user {}", userId, e);
            return Collections.emptyList();
        }
    }

    public void saveThreatIntel(ThreatIntel intel) {
        try {
            intel.setLastSeen(LocalDateTime.now());
            String json = objectMapper.writeValueAsString(intel);
            redisTemplate.opsForValue().set(THREAT_INTEL_PREFIX + intel.getIpAddress(), json, Duration.ofDays(7));
            log.debug("Saved threat intel for IP {}", intel.getIpAddress());
        } catch (Exception e) {
            log.error("Failed to save threat intel for IP {}", intel.getIpAddress(), e);
        }
    }

    public Optional<ThreatIntel> getThreatIntel(String ipAddress) {
        try {
            String json = redisTemplate.opsForValue().get(THREAT_INTEL_PREFIX + ipAddress);
            if (json == null) {
                return Optional.empty();
            }
            return Optional.of(objectMapper.readValue(json, ThreatIntel.class));
        } catch (Exception e) {
            log.error("Failed to get threat intel for IP {}", ipAddress, e);
            return Optional.empty();
        }
    }

    public void incrementThreatHit(String ipAddress) {
        String key = THREAT_INTEL_PREFIX + ipAddress;
        String json = redisTemplate.opsForValue().get(key);
        if (json != null) {
            try {
                ThreatIntel intel = objectMapper.readValue(json, ThreatIntel.class);
                intel.setHitCount(intel.getHitCount() + 1);
                intel.setLastSeen(LocalDateTime.now());
                saveThreatIntel(intel);
            } catch (Exception e) {
                log.error("Failed to increment threat hit for IP {}", ipAddress, e);
            }
        }
    }

    public void removeThreatIntel(String ipAddress) {
        redisTemplate.delete(THREAT_INTEL_PREFIX + ipAddress);
    }

    public List<ThreatIntel> getAllActiveThreats(int limit) {
        Set<String> keys = redisTemplate.keys(THREAT_INTEL_PREFIX + "*");
        if (keys == null || keys.isEmpty()) {
            return Collections.emptyList();
        }

        List<ThreatIntel> threats = new ArrayList<>();
        for (String key : keys.stream().limit(limit).collect(Collectors.toList())) {
            String json = redisTemplate.opsForValue().get(key);
            if (json != null) {
                try {
                    threats.add(objectMapper.readValue(json, ThreatIntel.class));
                } catch (Exception e) {
                    log.error("Failed to parse threat intel", e);
                }
            }
        }
        return threats;
    }
}
