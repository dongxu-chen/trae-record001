package com.sessionguard.service;

import com.sessionguard.config.SessionGuardProperties;
import com.sessionguard.model.LocationJumpDetection;
import com.sessionguard.model.SessionProfile;
import com.sessionguard.store.SessionStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class LocationJumpDetectionService {

    private final SessionStore sessionStore;
    private final SessionGuardProperties properties;

    private static final double COMMERCIAL_FLIGHT_SPEED_KMH = 900.0;
    private static final double HIGH_SPEED_RAIL_KMH = 350.0;
    private static final double CAR_SPEED_KMH = 120.0;

    private static final int LOW_SPEED_SCORE = 10;
    private static final int MEDIUM_SPEED_SCORE = 20;
    private static final int HIGH_SPEED_SCORE = 35;
    private static final int IMPOSSIBLE_SPEED_SCORE = 50;

    public LocationJumpDetection detectLocationJump(String userId, SessionProfile currentSession) {
        List<Map<String, Object>> locationHistory = sessionStore.getUserLocationHistory(userId, 5);

        if (locationHistory.isEmpty() || currentSession.getIpContext() == null) {
            return null;
        }

        Map<String, Object> lastLocation = locationHistory.get(locationHistory.size() - 1);
        String fromCountry = (String) lastLocation.get("country");
        String fromRegion = (String) lastLocation.get("region");
        String fromCity = (String) lastLocation.get("city");
        String fromIp = (String) lastLocation.get("ip");
        String timestampStr = (String) lastLocation.get("timestamp");

        String toCountry = currentSession.getIpContext().getGeoCountry();
        String toRegion = currentSession.getIpContext().getGeoRegion();
        String toCity = currentSession.getIpContext().getGeoCity();
        String toIp = currentSession.getIpContext().getIpAddress();

        if ("UNKNOWN".equals(fromCountry) || "UNKNOWN".equals(toCountry)) {
            return null;
        }

        if (fromCountry.equals(toCountry) && fromRegion.equals(toRegion) && fromCity.equals(toCity)) {
            return null;
        }

        LocalDateTime lastTime;
        try {
            lastTime = LocalDateTime.parse(timestampStr);
        } catch (Exception e) {
            lastTime = LocalDateTime.now().minusMinutes(1);
        }

        LocalDateTime currentTime = LocalDateTime.now();
        long timeGapMinutes = Duration.between(lastTime, currentTime).toMinutes();

        double estimatedDistanceKm = estimateDistance(fromCountry, fromCity, toCountry, toCity);
        double calculatedSpeedKmh = calculateSpeed(estimatedDistanceKm, timeGapMinutes);

        LocationJumpDetection.JumpLevel jumpLevel = determineJumpLevel(calculatedSpeedKmh, fromCountry, toCountry, timeGapMinutes);

        int riskScore = calculateRiskScore(jumpLevel, timeGapMinutes, fromCountry, toCountry);

        String fromLocation = buildLocationString(fromCountry, fromRegion, fromCity);
        String toLocation = buildLocationString(toCountry, toRegion, toCity);
        String description = buildDescription(jumpLevel, fromLocation, toLocation, calculatedSpeedKmh, timeGapMinutes);

        LocationJumpDetection detection = LocationJumpDetection.builder()
                .userId(userId)
                .sessionId(currentSession.getSessionId())
                .jumpLevel(jumpLevel)
                .calculatedSpeedKmh(calculatedSpeedKmh)
                .distanceKm(estimatedDistanceKm)
                .timeGapMinutes(timeGapMinutes)
                .fromLocation(fromLocation)
                .toLocation(toLocation)
                .fromIp(fromIp)
                .toIp(toIp)
                .detectedAt(LocalDateTime.now())
                .description(description)
                .riskScoreContribution(riskScore)
                .build();

        if (jumpLevel.getLevel() >= LocationJumpDetection.JumpLevel.MEDIUM.getLevel()) {
            sessionStore.saveLocationJumpDetection(detection);
            log.warn("Location jump detected for user {}: {} -> {} (speed: {:.0f} km/h, level: {})",
                    userId, fromLocation, toLocation, calculatedSpeedKmh, jumpLevel);
        }

        return detection;
    }

    public List<LocationJumpDetection> getJumpHistory(String userId) {
        return sessionStore.getLocationJumpHistory(userId);
    }

    private double estimateDistance(String fromCountry, String fromCity, String toCountry, String toCity) {
        Map<String, double[]> cityCoordinates = Map.ofEntries(
                Map.entry("Beijing", new double[]{39.9, 116.4}),
                Map.entry("Shanghai", new double[]{31.2, 121.5}),
                Map.entry("Guangzhou", new double[]{23.1, 113.3}),
                Map.entry("Shenzhen", new double[]{22.5, 114.1}),
                Map.entry("Chengdu", new double[]{30.7, 104.1}),
                Map.entry("Hangzhou", new double[]{30.3, 120.2}),
                Map.entry("Wuhan", new double[]{30.6, 114.3}),
                Map.entry("Xian", new double[]{34.3, 108.9}),
                Map.entry("Chongqing", new double[]{29.6, 106.5}),
                Map.entry("Nanjing", new double[]{32.1, 118.8}),
                Map.entry("Tokyo", new double[]{35.7, 139.7}),
                Map.entry("New York", new double[]{40.7, -74.0}),
                Map.entry("London", new double[]{51.5, -0.1}),
                Map.entry("Paris", new double[]{48.9, 2.3}),
                Map.entry("Singapore", new double[]{1.4, 103.8}),
                Map.entry("Hong Kong", new double[]{22.3, 114.2})
        );

        double[] fromCoords = cityCoordinates.getOrDefault(fromCity, getDefaultCoords(fromCountry));
        double[] toCoords = cityCoordinates.getOrDefault(toCity, getDefaultCoords(toCountry));

        return haversineDistance(fromCoords[0], fromCoords[1], toCoords[0], toCoords[1]);
    }

    private double[] getDefaultCoords(String country) {
        return switch (country) {
            case "CN" -> new double[]{35.9, 104.2};
            case "US" -> new double[]{37.1, -95.7};
            case "JP" -> new double[]{36.2, 138.3};
            case "GB" -> new double[]{54.0, -2.0};
            case "FR" -> new double[]{46.6, 1.9};
            case "DE" -> new double[]{51.2, 10.5};
            case "SG" -> new double[]{1.4, 103.8};
            default -> new double[]{0.0, 0.0};
        };
    }

    private double haversineDistance(double lat1, double lon1, double lat2, double lon2) {
        double R = 6371.0;
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    private double calculateSpeed(double distanceKm, long timeGapMinutes) {
        if (timeGapMinutes <= 0 || distanceKm <= 0) {
            return 0;
        }
        double hours = timeGapMinutes / 60.0;
        return distanceKm / hours;
    }

    private LocationJumpDetection.JumpLevel determineJumpLevel(double speedKmh, String fromCountry, String toCountry, long timeGapMinutes) {
        boolean sameCountry = fromCountry.equals(toCountry);

        if (speedKmh <= 0) {
            return LocationJumpDetection.JumpLevel.NONE;
        }

        if (timeGapMinutes < 15) {
            return LocationJumpDetection.JumpLevel.IMPOSSIBLE;
        }

        if (!sameCountry) {
            if (speedKmh > COMMERCIAL_FLIGHT_SPEED_KMH * 1.5) {
                return LocationJumpDetection.JumpLevel.IMPOSSIBLE;
            } else if (speedKmh > COMMERCIAL_FLIGHT_SPEED_KMH * 0.5) {
                return LocationJumpDetection.JumpLevel.HIGH;
            } else {
                return LocationJumpDetection.JumpLevel.MEDIUM;
            }
        }

        if (speedKmh > HIGH_SPEED_RAIL_KMH * 2) {
            return LocationJumpDetection.JumpLevel.IMPOSSIBLE;
        } else if (speedKmh > HIGH_SPEED_RAIL_KMH) {
            return LocationJumpDetection.JumpLevel.HIGH;
        } else if (speedKmh > CAR_SPEED_KMH) {
            return LocationJumpDetection.JumpLevel.MEDIUM;
        } else if (speedKmh > CAR_SPEED_KMH * 0.5) {
            return LocationJumpDetection.JumpLevel.LOW;
        }

        return LocationJumpDetection.JumpLevel.NONE;
    }

    private int calculateRiskScore(LocationJumpDetection.JumpLevel jumpLevel, long timeGapMinutes, String fromCountry, String toCountry) {
        int baseScore = switch (jumpLevel) {
            case NONE -> 0;
            case LOW -> LOW_SPEED_SCORE;
            case MEDIUM -> MEDIUM_SPEED_SCORE;
            case HIGH -> HIGH_SPEED_SCORE;
            case IMPOSSIBLE -> IMPOSSIBLE_SPEED_SCORE;
        };

        if (!fromCountry.equals(toCountry)) {
            baseScore += 10;
        }

        if (timeGapMinutes < 30) {
            baseScore += 10;
        }

        return Math.min(baseScore, 100);
    }

    private String buildLocationString(String country, String region, String city) {
        StringBuilder sb = new StringBuilder();
        if (city != null && !"UNKNOWN".equals(city)) {
            sb.append(city);
        }
        if (region != null && !"UNKNOWN".equals(region)) {
            if (!sb.isEmpty()) sb.append(", ");
            sb.append(region);
        }
        if (country != null && !"UNKNOWN".equals(country)) {
            if (!sb.isEmpty()) sb.append(", ");
            sb.append(country);
        }
        return sb.isEmpty() ? "UNKNOWN" : sb.toString();
    }

    private String buildDescription(LocationJumpDetection.JumpLevel level, String from, String to, double speed, long minutes) {
        String levelDesc = switch (level) {
            case NONE -> "正常位置变化";
            case LOW -> "轻微区域切换";
            case MEDIUM -> "跨区域快速切换";
            case HIGH -> "高速位置切换";
            case IMPOSSIBLE -> "物理不可能的位置跳跃";
        };
        return String.format("%s: %s -> %s (计算速度: %.0f km/h, 时间间隔: %d分钟)", levelDesc, from, to, speed, minutes);
    }
}
