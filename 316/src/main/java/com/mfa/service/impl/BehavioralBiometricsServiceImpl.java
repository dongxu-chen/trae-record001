package com.mfa.service.impl;

import com.mfa.dto.*;
import com.mfa.entity.User;
import com.mfa.enums.RiskLevel;
import com.mfa.service.BehavioralBiometricsService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class BehavioralBiometricsServiceImpl implements BehavioralBiometricsService {

    private static final String PROFILE_KEY_PREFIX = "mfa:behavior:profile:";
    private static final String ANALYSIS_KEY_PREFIX = "mfa:behavior:analysis:";
    private static final int PROFILE_EXPIRE_DAYS = 90;
    private static final int ANALYSIS_EXPIRE_HOURS = 24;
    private static final int CALIBRATION_REQUIRED_SAMPLES = 5;
    private static final double HIGH_SIMILARITY_THRESHOLD = 0.85;
    private static final double MEDIUM_SIMILARITY_THRESHOLD = 0.65;

    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper;

    @Override
    public BehavioralBiometrics analyzeBehavior(BehavioralDataRequest request, User user) {
        log.debug("Analyzing behavioral data for user: {}", user != null ? user.getUsername() : "anonymous");

        BehavioralProfile currentProfile = extractProfile(request);
        BehavioralProfile baselineProfile = getUserProfile(user != null ? user.getId().toString() : null);

        double similarityScore = 0.0;
        if (baselineProfile != null && baselineProfile.getIsCalibrated()) {
            similarityScore = calculateSimilarity(baselineProfile, currentProfile);
        }

        RiskAssessment riskAssessment = assessBehaviorRisk(
                BehavioralBiometrics.builder()
                        .baselineProfile(baselineProfile)
                        .currentProfile(currentProfile)
                        .similarityScore(similarityScore)
                        .build()
        );

        BehavioralBiometrics result = BehavioralBiometrics.builder()
                .sessionId(request.getSessionId())
                .userId(user != null ? user.getId().toString() : null)
                .keystrokeDynamics(request.getKeystrokeDynamics())
                .mouseDynamics(request.getMouseDynamics())
                .baselineProfile(baselineProfile)
                .currentProfile(currentProfile)
                .similarityScore(similarityScore)
                .riskScore(riskAssessment.getScore())
                .riskLevel(riskAssessment.getLevel())
                .timestamp(LocalDateTime.now())
                .deviceFingerprint(request.getDeviceFingerprint())
                .build();

        String key = ANALYSIS_KEY_PREFIX + request.getSessionId();
        redisTemplate.opsForValue().set(key, result, ANALYSIS_EXPIRE_HOURS, TimeUnit.HOURS);

        if (user != null && Boolean.TRUE.equals(request.getForCalibration())) {
            updateProfile(user.getId().toString(), result);
        }

        log.debug("Behavioral analysis complete for session: {}, similarity: {}, risk: {}",
                request.getSessionId(), similarityScore, riskAssessment.getLevel());

        return result;
    }

    @Override
    public BehavioralProfile getUserProfile(String userId) {
        if (userId == null) {
            return null;
        }
        String key = PROFILE_KEY_PREFIX + userId;
        Object obj = redisTemplate.opsForValue().get(key);
        if (obj == null) {
            return null;
        }
        return objectMapper.convertValue(obj, BehavioralProfile.class);
    }

    @Override
    public void updateProfile(String userId, BehavioralBiometrics biometrics) {
        if (userId == null || biometrics.getCurrentProfile() == null) {
            return;
        }

        BehavioralProfile existing = getUserProfile(userId);
        BehavioralProfile current = biometrics.getCurrentProfile();
        BehavioralProfile updated;

        if (existing == null) {
            updated = BehavioralProfile.builder()
                    .avgHoldTime(current.getAvgHoldTime())
                    .avgHoldTimeStdDev(current.getAvgHoldTimeStdDev())
                    .avgFlightTime(current.getAvgFlightTime())
                    .avgFlightTimeStdDev(current.getAvgFlightTimeStdDev())
                    .typingSpeedCps(current.getTypingSpeedCps())
                    .typingSpeedStdDev(current.getTypingSpeedStdDev())
                    .avgMouseSpeed(current.getAvgMouseSpeed())
                    .avgMouseSpeedStdDev(current.getAvgMouseSpeedStdDev())
                    .avgMouseAcceleration(current.getAvgMouseAcceleration())
                    .pathEfficiency(current.getPathEfficiency())
                    .avgClickInterval(current.getAvgClickInterval())
                    .sampleCount(1)
                    .isCalibrated(false)
                    .lastUpdated(System.currentTimeMillis())
                    .build();
        } else {
            int newSampleCount = existing.getSampleCount() + 1;
            updated = BehavioralProfile.builder()
                    .avgHoldTime(updateAverage(existing.getAvgHoldTime(), current.getAvgHoldTime(), existing.getSampleCount()))
                    .avgHoldTimeStdDev(updateStdDev(existing.getAvgHoldTimeStdDev(), current.getAvgHoldTimeStdDev(), existing.getSampleCount()))
                    .avgFlightTime(updateAverage(existing.getAvgFlightTime(), current.getAvgFlightTime(), existing.getSampleCount()))
                    .avgFlightTimeStdDev(updateStdDev(existing.getAvgFlightTimeStdDev(), current.getAvgFlightTimeStdDev(), existing.getSampleCount()))
                    .typingSpeedCps(updateAverage(existing.getTypingSpeedCps(), current.getTypingSpeedCps(), existing.getSampleCount()))
                    .typingSpeedStdDev(updateStdDev(existing.getTypingSpeedStdDev(), current.getTypingSpeedStdDev(), existing.getSampleCount()))
                    .avgMouseSpeed(updateAverage(existing.getAvgMouseSpeed(), current.getAvgMouseSpeed(), existing.getSampleCount()))
                    .avgMouseSpeedStdDev(updateStdDev(existing.getAvgMouseSpeedStdDev(), current.getAvgMouseSpeedStdDev(), existing.getSampleCount()))
                    .avgMouseAcceleration(updateAverage(existing.getAvgMouseAcceleration(), current.getAvgMouseAcceleration(), existing.getSampleCount()))
                    .pathEfficiency(updateAverage(existing.getPathEfficiency(), current.getPathEfficiency(), existing.getSampleCount()))
                    .avgClickInterval(updateAverage(existing.getAvgClickInterval(), current.getAvgClickInterval(), existing.getSampleCount()))
                    .sampleCount(newSampleCount)
                    .isCalibrated(newSampleCount >= CALIBRATION_REQUIRED_SAMPLES)
                    .lastUpdated(System.currentTimeMillis())
                    .build();
        }

        String key = PROFILE_KEY_PREFIX + userId;
        redisTemplate.opsForValue().set(key, updated, PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);
        log.debug("Updated behavioral profile for user: {}, sample count: {}", userId, updated.getSampleCount());
    }

    @Override
    public RiskAssessment assessBehaviorRisk(BehavioralBiometrics biometrics) {
        int riskScore = 0;
        java.util.List<String> riskFactors = new java.util.ArrayList<>();
        java.util.Map<String, Object> details = new java.util.HashMap<>();

        BehavioralProfile baseline = biometrics.getBaselineProfile();
        BehavioralProfile current = biometrics.getCurrentProfile();
        double similarity = biometrics.getSimilarityScore();

        if (baseline == null || !baseline.getIsCalibrated()) {
            return RiskAssessment.builder()
                    .score(0)
                    .level(RiskLevel.LOW.name())
                    .riskFactors(java.util.Collections.emptyList())
                    .details(details)
                    .stepUpRequired(false)
                    .build();
        }

        details.put("similarityScore", similarity);

        if (similarity < MEDIUM_SIMILARITY_THRESHOLD) {
            riskScore += 40;
            riskFactors.add("BEHAVIOR_SIMILARITY_LOW");
            details.put("behaviorDeviation", "HIGH");
        } else if (similarity < HIGH_SIMILARITY_THRESHOLD) {
            riskScore += 20;
            riskFactors.add("BEHAVIOR_SIMILARITY_MEDIUM");
            details.put("behaviorDeviation", "MEDIUM");
        }

        if (current.getTypingSpeedCps() != null && baseline.getTypingSpeedCps() != null) {
            double speedRatio = current.getTypingSpeedCps() / baseline.getTypingSpeedCps();
            if (speedRatio > 2.0 || speedRatio < 0.3) {
                riskScore += 15;
                riskFactors.add("TYPING_SPEED_ANOMALY");
                details.put("typingSpeedRatio", speedRatio);
            }
        }

        if (current.getAvgHoldTime() != null && baseline.getAvgHoldTime() != null) {
            double holdTimeRatio = current.getAvgHoldTime() / baseline.getAvgHoldTime();
            if (holdTimeRatio > 2.5 || holdTimeRatio < 0.25) {
                riskScore += 15;
                riskFactors.add("KEY_HOLD_TIME_ANOMALY");
                details.put("holdTimeRatio", holdTimeRatio);
            }
        }

        if (current.getPathEfficiency() != null && current.getPathEfficiency() < 0.3) {
            riskScore += 10;
            riskFactors.add("MOUSE_PATH_INEFFICIENT");
            details.put("pathEfficiency", current.getPathEfficiency());
        }

        if (current.getAvgMouseSpeed() != null && baseline.getAvgMouseSpeed() != null) {
            double speedRatio = current.getAvgMouseSpeed() / baseline.getAvgMouseSpeed();
            if (speedRatio > 3.0 || speedRatio < 0.2) {
                riskScore += 10;
                riskFactors.add("MOUSE_SPEED_ANOMALY");
                details.put("mouseSpeedRatio", speedRatio);
            }
        }

        RiskLevel riskLevel;
        if (riskScore >= 60) {
            riskLevel = RiskLevel.HIGH;
        } else if (riskScore >= 30) {
            riskLevel = RiskLevel.MEDIUM;
        } else {
            riskLevel = RiskLevel.LOW;
        }

        return RiskAssessment.builder()
                .score(riskScore)
                .level(riskLevel.name())
                .riskFactors(riskFactors)
                .details(details)
                .stepUpRequired(riskLevel == RiskLevel.HIGH)
                .build();
    }

    @Override
    public double calculateSimilarity(BehavioralProfile baseline, BehavioralProfile current) {
        if (baseline == null || current == null) {
            return 0.0;
        }

        double totalWeight = 0;
        double weightedScore = 0;

        if (baseline.getAvgHoldTime() != null && current.getAvgHoldTime() != null
                && baseline.getAvgHoldTimeStdDev() != null) {
            double weight = 0.20;
            double score = calculateZScoreSimilarity(
                    baseline.getAvgHoldTime(),
                    baseline.getAvgHoldTimeStdDev(),
                    current.getAvgHoldTime()
            );
            weightedScore += weight * score;
            totalWeight += weight;
        }

        if (baseline.getAvgFlightTime() != null && current.getAvgFlightTime() != null
                && baseline.getAvgFlightTimeStdDev() != null) {
            double weight = 0.20;
            double score = calculateZScoreSimilarity(
                    baseline.getAvgFlightTime(),
                    baseline.getAvgFlightTimeStdDev(),
                    current.getAvgFlightTime()
            );
            weightedScore += weight * score;
            totalWeight += weight;
        }

        if (baseline.getTypingSpeedCps() != null && current.getTypingSpeedCps() != null
                && baseline.getTypingSpeedStdDev() != null) {
            double weight = 0.20;
            double score = calculateZScoreSimilarity(
                    baseline.getTypingSpeedCps(),
                    baseline.getTypingSpeedStdDev(),
                    current.getTypingSpeedCps()
            );
            weightedScore += weight * score;
            totalWeight += weight;
        }

        if (baseline.getAvgMouseSpeed() != null && current.getAvgMouseSpeed() != null
                && baseline.getAvgMouseSpeedStdDev() != null) {
            double weight = 0.15;
            double score = calculateZScoreSimilarity(
                    baseline.getAvgMouseSpeed(),
                    baseline.getAvgMouseSpeedStdDev(),
                    current.getAvgMouseSpeed()
            );
            weightedScore += weight * score;
            totalWeight += weight;
        }

        if (baseline.getPathEfficiency() != null && current.getPathEfficiency() != null) {
            double weight = 0.15;
            double diff = Math.abs(baseline.getPathEfficiency() - current.getPathEfficiency());
            double score = Math.max(0, 1 - diff * 2);
            weightedScore += weight * score;
            totalWeight += weight;
        }

        if (baseline.getAvgClickInterval() != null && current.getAvgClickInterval() != null) {
            double weight = 0.10;
            double ratio = Math.min(baseline.getAvgClickInterval(), current.getAvgClickInterval())
                    / Math.max(baseline.getAvgClickInterval(), current.getAvgClickInterval());
            weightedScore += weight * ratio;
            totalWeight += weight;
        }

        if (baseline.getAvgMouseAcceleration() != null && current.getAvgMouseAcceleration() != null) {
            double weight = 0.05;
            double ratio = Math.min(baseline.getAvgMouseAcceleration(), current.getAvgMouseAcceleration())
                    / Math.max(baseline.getAvgMouseAcceleration(), current.getAvgMouseAcceleration());
            weightedScore += weight * ratio;
            totalWeight += weight;
        }

        return totalWeight > 0 ? weightedScore / totalWeight : 0.0;
    }

    @Override
    public void calibrateProfile(String userId, BehavioralDataRequest request) {
        BehavioralProfile current = extractProfile(request);
        BehavioralProfile existing = getUserProfile(userId);

        if (existing == null) {
            existing = BehavioralProfile.builder()
                    .sampleCount(0)
                    .isCalibrated(false)
                    .build();
        }

        int newSampleCount = existing.getSampleCount() + 1;
        BehavioralProfile updated = BehavioralProfile.builder()
                .avgHoldTime(updateAverage(existing.getAvgHoldTime(), current.getAvgHoldTime(), existing.getSampleCount()))
                .avgHoldTimeStdDev(updateStdDev(existing.getAvgHoldTimeStdDev(), current.getAvgHoldTimeStdDev(), existing.getSampleCount()))
                .avgFlightTime(updateAverage(existing.getAvgFlightTime(), current.getAvgFlightTime(), existing.getSampleCount()))
                .avgFlightTimeStdDev(updateStdDev(existing.getAvgFlightTimeStdDev(), current.getAvgFlightTimeStdDev(), existing.getSampleCount()))
                .typingSpeedCps(updateAverage(existing.getTypingSpeedCps(), current.getTypingSpeedCps(), existing.getSampleCount()))
                .typingSpeedStdDev(updateStdDev(existing.getTypingSpeedStdDev(), current.getTypingSpeedStdDev(), existing.getSampleCount()))
                .avgMouseSpeed(updateAverage(existing.getAvgMouseSpeed(), current.getAvgMouseSpeed(), existing.getSampleCount()))
                .avgMouseSpeedStdDev(updateStdDev(existing.getAvgMouseSpeedStdDev(), current.getAvgMouseSpeedStdDev(), existing.getSampleCount()))
                .avgMouseAcceleration(updateAverage(existing.getAvgMouseAcceleration(), current.getAvgMouseAcceleration(), existing.getSampleCount()))
                .pathEfficiency(updateAverage(existing.getPathEfficiency(), current.getPathEfficiency(), existing.getSampleCount()))
                .avgClickInterval(updateAverage(existing.getAvgClickInterval(), current.getAvgClickInterval(), existing.getSampleCount()))
                .sampleCount(newSampleCount)
                .isCalibrated(newSampleCount >= CALIBRATION_REQUIRED_SAMPLES)
                .lastUpdated(System.currentTimeMillis())
                .build();

        String key = PROFILE_KEY_PREFIX + userId;
        redisTemplate.opsForValue().set(key, updated, PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);

        log.info("Calibrated behavioral profile for user: {}, sample count: {}, calibrated: {}",
                userId, newSampleCount, updated.getIsCalibrated());
    }

    @Override
    public boolean isProfileCalibrated(String userId) {
        BehavioralProfile profile = getUserProfile(userId);
        return profile != null && Boolean.TRUE.equals(profile.getIsCalibrated());
    }

    private BehavioralProfile extractProfile(BehavioralDataRequest request) {
        BehavioralProfile.BehavioralProfileBuilder builder = BehavioralProfile.builder();

        KeystrokeDynamics keystroke = request.getKeystrokeDynamics();
        if (keystroke != null) {
            builder.avgHoldTime(keystroke.getAvgHoldTime());
            builder.avgHoldTimeStdDev(keystroke.getStdDevHoldTime());
            builder.avgFlightTime(keystroke.getAvgFlightTime());
            builder.avgFlightTimeStdDev(keystroke.getStdDevFlightTime());
            builder.typingSpeedCps(keystroke.getTypingSpeedCps());

            if (keystroke.getHoldTimes() != null && !keystroke.getHoldTimes().isEmpty()) {
                builder.typingSpeedStdDev(calculateStdDev(keystroke.getHoldTimes()));
            }
        }

        MouseDynamics mouse = request.getMouseDynamics();
        if (mouse != null) {
            builder.avgMouseSpeed(mouse.getAvgSpeed());
            builder.avgMouseAcceleration(mouse.getAvgAcceleration());
            builder.pathEfficiency(mouse.getPathEfficiency());
            builder.avgClickInterval(mouse.getAvgClickInterval());

            if (mouse.getSpeedProfile() != null && !mouse.getSpeedProfile().isEmpty()) {
                builder.avgMouseSpeedStdDev(calculateStdDev(mouse.getSpeedProfile()));
            }
        }

        return builder.build();
    }

    private double calculateZScoreSimilarity(double mean, double stdDev, double value) {
        if (stdDev == 0) {
            return mean == value ? 1.0 : 0.0;
        }
        double zScore = Math.abs((value - mean) / stdDev);
        if (zScore <= 1) {
            return 1.0 - zScore * 0.5;
        } else if (zScore <= 2) {
            return 0.5 - (zScore - 1) * 0.35;
        } else if (zScore <= 3) {
            return 0.15 - (zScore - 2) * 0.15;
        }
        return 0.0;
    }

    private Double updateAverage(Double existing, Double newValue, int sampleCount) {
        if (existing == null) {
            return newValue;
        }
        if (newValue == null) {
            return existing;
        }
        return (existing * sampleCount + newValue) / (sampleCount + 1);
    }

    private Double updateStdDev(Double existing, Double newValue, int sampleCount) {
        if (existing == null) {
            return newValue;
        }
        if (newValue == null) {
            return existing;
        }
        return (existing * sampleCount + newValue) / (sampleCount + 1);
    }

    private double calculateStdDev(List<Double> values) {
        if (values == null || values.size() < 2) {
            return 0.0;
        }
        double mean = values.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
        double variance = values.stream()
                .mapToDouble(v -> Math.pow(v - mean, 2))
                .average()
                .orElse(0.0);
        return Math.sqrt(variance);
    }
}
