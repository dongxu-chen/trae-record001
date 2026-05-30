package com.sessionguard.service;

import com.sessionguard.model.*;
import com.sessionguard.store.SessionStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class BehaviorLearningService {

    private final SessionStore sessionStore;

    private static final int MIN_SESSIONS_FOR_BASELINE = 5;
    private static final int MAX_COMMON_ITEMS = 10;

    @Async
    public void updateBehaviorBaseline(String userId, SessionProfile currentSession) {
        try {
            UserBehaviorBaseline existing = sessionStore.getBehaviorBaseline(userId).orElse(null);

            UserBehaviorBaseline baseline;
            if (existing == null) {
                baseline = createInitialBaseline(userId, currentSession);
            } else {
                baseline = updateExistingBaseline(existing, currentSession);
            }

            sessionStore.saveBehaviorBaseline(baseline);
            log.debug("Behavior baseline updated for user {}, version {}", userId, baseline.getVersion());
        } catch (Exception e) {
            log.error("Failed to update behavior baseline for user {}", userId, e);
        }
    }

    public BaselineDeviationScore calculateDeviation(String userId, SessionProfile currentSession) {
        UserBehaviorBaseline baseline = sessionStore.getBehaviorBaseline(userId).orElse(null);
        if (baseline == null || baseline.getStats() == null || !baseline.getStats().isBaselineStable()) {
            return new BaselineDeviationScore(0, Collections.emptyList());
        }

        List<String> deviations = new ArrayList<>();
        int deviationScore = 0;

        deviationScore += checkIpDeviation(baseline, currentSession, deviations);
        deviationScore += checkDeviceDeviation(baseline, currentSession, deviations);
        deviationScore += checkTimeDeviation(baseline, currentSession, deviations);

        return new BaselineDeviationScore(Math.min(deviationScore, 100), deviations);
    }

    public void saveUserLocation(String userId, String country, String region, String city, String ip) {
        sessionStore.saveUserLocation(userId, country, region, city, ip);
    }

    public Optional<UserBehaviorBaseline> getBaseline(String userId) {
        return sessionStore.getBehaviorBaseline(userId);
    }

    private UserBehaviorBaseline createInitialBaseline(String userId, SessionProfile session) {
        LocalDateTime now = LocalDateTime.now();

        Set<String> commonIps = new HashSet<>();
        Set<String> commonSubnets = new HashSet<>();
        Set<String> commonCountries = new HashSet<>();
        Set<String> commonBrowsers = new HashSet<>();
        Set<String> commonPlatforms = new HashSet<>();
        Set<String> activeHours = new HashSet<>();

        if (session.getIpContext() != null) {
            commonIps.add(session.getIpContext().getIpAddress());
            commonSubnets.add(session.getIpContext().getSubnetPrefix());
            commonCountries.add(session.getIpContext().getGeoCountry());
        }

        if (session.getDeviceFingerprint() != null) {
            commonBrowsers.add(session.getDeviceFingerprint().getBrowser());
            commonPlatforms.add(session.getDeviceFingerprint().getPlatform());
        }

        activeHours.add(String.valueOf(now.getHour()));

        return UserBehaviorBaseline.builder()
                .userId(userId)
                .ipPattern(UserBehaviorBaseline.IpPattern.builder()
                        .commonIps(commonIps)
                        .commonSubnets(commonSubnets)
                        .commonCountries(commonCountries)
                        .commonRegions(new HashSet<>())
                        .commonCities(new HashSet<>())
                        .knownIsps(new HashSet<>())
                        .proxyUsageRate(0.0)
                        .vpnUsageRate(0.0)
                        .build())
                .devicePattern(UserBehaviorBaseline.DevicePattern.builder()
                        .commonFingerprintHashes(new HashSet<>())
                        .commonBrowsers(commonBrowsers)
                        .commonPlatforms(commonPlatforms)
                        .commonOs(new HashSet<>())
                        .commonTimezones(new HashSet<>())
                        .commonLanguages(new HashSet<>())
                        .mostCommonScreen("")
                        .deviceChangeFrequency(0.0)
                        .build())
                .timePattern(UserBehaviorBaseline.TimePattern.builder()
                        .activeHours(activeHours)
                        .activeDays(new HashSet<>())
                        .avgSessionDurationMinutes(0)
                        .avgAccessCountPerSession(session.getAccessCount())
                        .maxDailySessions(1)
                        .avgSessionIntervalMinutes(0)
                        .build())
                .stats(UserBehaviorBaseline.BehaviorStats.builder()
                        .totalSessions(1)
                        .totalAccessCount(session.getAccessCount())
                        .learningDays(0)
                        .ipVariabilityScore(0)
                        .deviceVariabilityScore(0)
                        .anomalyRate(0.0)
                        .baselineStable(false)
                        .recentLocations(new ArrayList<>())
                        .build())
                .createdAt(now)
                .lastUpdatedAt(now)
                .version(1)
                .build();
    }

    private UserBehaviorBaseline updateExistingBaseline(UserBehaviorBaseline baseline, SessionProfile session) {
        baseline.setVersion(baseline.getVersion() + 1);

        UserBehaviorBaseline.IpPattern ipPattern = baseline.getIpPattern();
        UserBehaviorBaseline.DevicePattern devicePattern = baseline.getDevicePattern();
        UserBehaviorBaseline.TimePattern timePattern = baseline.getTimePattern();
        UserBehaviorBaseline.BehaviorStats stats = baseline.getStats();

        if (ipPattern.getCommonIps() == null) ipPattern.setCommonIps(new HashSet<>());
        if (ipPattern.getCommonSubnets() == null) ipPattern.setCommonSubnets(new HashSet<>());
        if (ipPattern.getCommonCountries() == null) ipPattern.setCommonCountries(new HashSet<>());
        if (ipPattern.getCommonRegions() == null) ipPattern.setCommonRegions(new HashSet<>());
        if (ipPattern.getCommonCities() == null) ipPattern.setCommonCities(new HashSet<>());
        if (ipPattern.getKnownIsps() == null) ipPattern.setKnownIsps(new HashSet<>());

        if (session.getIpContext() != null) {
            addWithLimit(ipPattern.getCommonIps(), session.getIpContext().getIpAddress(), MAX_COMMON_ITEMS);
            addWithLimit(ipPattern.getCommonSubnets(), session.getIpContext().getSubnetPrefix(), MAX_COMMON_ITEMS);
            addWithLimit(ipPattern.getCommonCountries(), session.getIpContext().getGeoCountry(), MAX_COMMON_ITEMS);
            addWithLimit(ipPattern.getCommonRegions(), session.getIpContext().getGeoRegion(), MAX_COMMON_ITEMS);
            addWithLimit(ipPattern.getCommonCities(), session.getIpContext().getGeoCity(), MAX_COMMON_ITEMS);
            addWithLimit(ipPattern.getKnownIsps(), session.getIpContext().getIsp(), MAX_COMMON_ITEMS);
        }

        if (devicePattern.getCommonBrowsers() == null) devicePattern.setCommonBrowsers(new HashSet<>());
        if (devicePattern.getCommonPlatforms() == null) devicePattern.setCommonPlatforms(new HashSet<>());
        if (devicePattern.getCommonOs() == null) devicePattern.setCommonOs(new HashSet<>());
        if (devicePattern.getCommonTimezones() == null) devicePattern.setCommonTimezones(new HashSet<>());
        if (devicePattern.getCommonLanguages() == null) devicePattern.setCommonLanguages(new HashSet<>());
        if (devicePattern.getCommonFingerprintHashes() == null) devicePattern.setCommonFingerprintHashes(new HashSet<>());

        if (session.getDeviceFingerprint() != null) {
            addWithLimit(devicePattern.getCommonFingerprintHashes(), session.getDeviceFingerprint().getFingerprintHash(), MAX_COMMON_ITEMS);
            addWithLimit(devicePattern.getCommonBrowsers(), session.getDeviceFingerprint().getBrowser(), MAX_COMMON_ITEMS);
            addWithLimit(devicePattern.getCommonPlatforms(), session.getDeviceFingerprint().getPlatform(), MAX_COMMON_ITEMS);
            addWithLimit(devicePattern.getCommonOs(), session.getDeviceFingerprint().getOs(), MAX_COMMON_ITEMS);
            addWithLimit(devicePattern.getCommonTimezones(), session.getDeviceFingerprint().getTimezone(), MAX_COMMON_ITEMS);
            addWithLimit(devicePattern.getCommonLanguages(), session.getDeviceFingerprint().getLanguage(), MAX_COMMON_ITEMS);
        }

        if (timePattern.getActiveHours() == null) timePattern.setActiveHours(new HashSet<>());
        if (timePattern.getActiveDays() == null) timePattern.setActiveDays(new HashSet<>());

        int hour = LocalDateTime.now().getHour();
        timePattern.getActiveHours().add(String.valueOf(hour));
        if (timePattern.getActiveHours().size() > MAX_COMMON_ITEMS) {
            Iterator<String> it = timePattern.getActiveHours().iterator();
            if (it.hasNext()) it.remove();
        }

        stats.setTotalSessions(stats.getTotalSessions() + 1);
        stats.setTotalAccessCount(stats.getTotalAccessCount() + session.getAccessCount());

        long daysSinceCreation = ChronoUnit.DAYS.between(baseline.getCreatedAt(), LocalDateTime.now());
        stats.setLearningDays((int) Math.max(1, daysSinceCreation));
        stats.setBaselineStable(stats.getTotalSessions() >= MIN_SESSIONS_FOR_BASELINE);

        stats.setIpVariabilityScore(calculateVariability(ipPattern.getCommonIps().size(), ipPattern.getCommonSubnets().size()));
        stats.setDeviceVariabilityScore(calculateVariability(devicePattern.getCommonFingerprintHashes().size(), devicePattern.getCommonBrowsers().size()));

        if (session.getIpContext() != null) {
            if (stats.getRecentLocations() == null) {
                stats.setRecentLocations(new ArrayList<>());
            }
            String loc = session.getIpContext().getGeoCountry() + ":" + session.getIpContext().getGeoCity();
            if (!stats.getRecentLocations().contains(loc)) {
                stats.getRecentLocations().add(loc);
                if (stats.getRecentLocations().size() > 5) {
                    stats.getRecentLocations().remove(0);
                }
            }
        }

        return baseline;
    }

    private <T> void addWithLimit(Set<T> set, T item, int max) {
        if (item == null) return;
        set.add(item);
        if (set.size() > max) {
            Iterator<T> it = set.iterator();
            if (it.hasNext()) it.next();
            if (it.hasNext()) it.remove();
        }
    }

    private int calculateVariability(int uniqueCount, int categoryCount) {
        double variability = (uniqueCount * 10.0 + categoryCount * 5.0) / 2.0;
        return Math.min((int) variability, 100);
    }

    private int checkIpDeviation(UserBehaviorBaseline baseline, SessionProfile session, List<String> deviations) {
        int score = 0;
        UserBehaviorBaseline.IpPattern ipPattern = baseline.getIpPattern();

        if (session.getIpContext() == null || ipPattern == null) {
            return 0;
        }

        if (!ipPattern.getCommonIps().isEmpty() && !ipPattern.getCommonIps().contains(session.getIpContext().getIpAddress())) {
            score += 15;
            deviations.add("Uncommon IP address: " + session.getIpContext().getIpAddress());
        }

        if (!ipPattern.getCommonSubnets().isEmpty() && !ipPattern.getCommonSubnets().contains(session.getIpContext().getSubnetPrefix())) {
            score += 10;
            deviations.add("Uncommon subnet: " + session.getIpContext().getSubnetPrefix());
        }

        if (!ipPattern.getCommonCountries().isEmpty() && !"UNKNOWN".equals(session.getIpContext().getGeoCountry())
                && !ipPattern.getCommonCountries().contains(session.getIpContext().getGeoCountry())) {
            score += 25;
            deviations.add("Unusual country: " + session.getIpContext().getGeoCountry());
        }

        return score;
    }

    private int checkDeviceDeviation(UserBehaviorBaseline baseline, SessionProfile session, List<String> deviations) {
        int score = 0;
        UserBehaviorBaseline.DevicePattern devicePattern = baseline.getDevicePattern();

        if (session.getDeviceFingerprint() == null || devicePattern == null) {
            return 0;
        }

        if (!devicePattern.getCommonBrowsers().isEmpty() && !devicePattern.getCommonBrowsers().contains(session.getDeviceFingerprint().getBrowser())) {
            score += 10;
            deviations.add("Uncommon browser: " + session.getDeviceFingerprint().getBrowser());
        }

        if (!devicePattern.getCommonOs().isEmpty() && !devicePattern.getCommonOs().contains(session.getDeviceFingerprint().getOs())) {
            score += 15;
            deviations.add("Uncommon OS: " + session.getDeviceFingerprint().getOs());
        }

        if (!devicePattern.getCommonTimezones().isEmpty() && !devicePattern.getCommonTimezones().contains(session.getDeviceFingerprint().getTimezone())) {
            score += 10;
            deviations.add("Uncommon timezone: " + session.getDeviceFingerprint().getTimezone());
        }

        return score;
    }

    private int checkTimeDeviation(UserBehaviorBaseline baseline, SessionProfile session, List<String> deviations) {
        int score = 0;
        UserBehaviorBaseline.TimePattern timePattern = baseline.getTimePattern();

        if (timePattern == null || timePattern.getActiveHours().isEmpty()) {
            return 0;
        }

        int currentHour = LocalDateTime.now().getHour();
        if (!timePattern.getActiveHours().contains(String.valueOf(currentHour))) {
            score += 10;
            deviations.add("Activity at unusual hour: " + currentHour);
        }

        return score;
    }

    public record BaselineDeviationScore(int totalScore, List<String> deviations) {}
}
