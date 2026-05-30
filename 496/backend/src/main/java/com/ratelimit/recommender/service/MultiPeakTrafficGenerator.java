package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.MultiPeakTrafficPattern;
import com.ratelimit.recommender.model.TimeSeriesPoint;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class MultiPeakTrafficGenerator {

    private final Random random = new Random();
    private final Map<String, List<MultiPeakTrafficPattern.BurstEvent>> activeBursts = new HashMap<>();

    public MultiPeakTrafficPattern generateTrafficPattern(String serviceId) {
        double baselineQps = getBaselineQpsForService(serviceId);

        List<MultiPeakTrafficPattern.PeriodicPeak> peaks = generatePeriodicPeaks(serviceId);
        List<MultiPeakTrafficPattern.BurstEvent> bursts = generateBurstEvents(serviceId);

        MultiPeakTrafficPattern.TrafficType type = determineTrafficType(serviceId);

        return MultiPeakTrafficPattern.builder()
                .serviceId(serviceId)
                .periodicPeaks(peaks)
                .burstEvents(bursts)
                .baselineQps(baselineQps)
                .variance(0.15 + random.nextDouble() * 0.2)
                .trafficType(type)
                .build();
    }

    private List<MultiPeakTrafficPattern.PeriodicPeak> generatePeriodicPeaks(String serviceId) {
        List<MultiPeakTrafficPattern.PeriodicPeak> peaks = new ArrayList<>();

        peaks.add(MultiPeakTrafficPattern.PeriodicPeak.builder()
                .name("早高峰")
                .startHour(8)
                .endHour(11)
                .intensity(1.5 + random.nextDouble() * 0.5)
                .width(2.0)
                .daysOfWeek(Arrays.asList(1, 2, 3, 4, 5))
                .build());

        peaks.add(MultiPeakTrafficPattern.PeriodicPeak.builder()
                .name("午高峰")
                .startHour(12)
                .endHour(14)
                .intensity(1.2 + random.nextDouble() * 0.3)
                .width(1.5)
                .daysOfWeek(Arrays.asList(1, 2, 3, 4, 5, 6, 7))
                .build());

        peaks.add(MultiPeakTrafficPattern.PeriodicPeak.builder()
                .name("晚高峰")
                .startHour(17)
                .endHour(21)
                .intensity(1.8 + random.nextDouble() * 0.7)
                .width(3.0)
                .daysOfWeek(Arrays.asList(1, 2, 3, 4, 5, 6))
                .build());

        peaks.add(MultiPeakTrafficPattern.PeriodicPeak.builder()
                .name("夜间低峰")
                .startHour(2)
                .endHour(6)
                .intensity(0.2 + random.nextDouble() * 0.1)
                .width(4.0)
                .daysOfWeek(Arrays.asList(1, 2, 3, 4, 5, 6, 7))
                .build());

        return peaks;
    }

    private List<MultiPeakTrafficPattern.BurstEvent> generateBurstEvents(String serviceId) {
        List<MultiPeakTrafficPattern.BurstEvent> bursts = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();

        bursts.add(MultiPeakTrafficPattern.BurstEvent.builder()
                .id("burst-" + UUID.randomUUID())
                .startTime(now.plusMinutes(15))
                .durationMinutes(10)
                .intensity(2.5 + random.nextDouble() * 2)
                .type(MultiPeakTrafficPattern.BurstType.FLASH_SALE)
                .description("模拟秒杀活动")
                .build());

        bursts.add(MultiPeakTrafficPattern.BurstEvent.builder()
                .id("burst-" + UUID.randomUUID())
                .startTime(now.plusMinutes(45))
                .durationMinutes(5)
                .intensity(3.0 + random.nextDouble() * 3)
                .type(MultiPeakTrafficPattern.BurstType.MARKETING_PUSH)
                .description("营销推送突发流量")
                .build());

        bursts.add(MultiPeakTrafficPattern.BurstEvent.builder()
                .id("burst-" + UUID.randomUUID())
                .startTime(now.plusMinutes(75))
                .durationMinutes(3)
                .intensity(1.5 + random.nextDouble())
                .type(MultiPeakTrafficPattern.BurstType.RANDOM_SPIKE)
                .description("随机流量尖峰")
                .build());

        return bursts;
    }

    private double getBaselineQpsForService(String serviceId) {
        switch (serviceId) {
            case "gateway": return 400;
            case "user-service": return 150;
            case "order-service": return 120;
            case "product-service": return 140;
            case "payment-service": return 60;
            default: return 80;
        }
    }

    private MultiPeakTrafficPattern.TrafficType determineTrafficType(String serviceId) {
        switch (serviceId) {
            case "gateway":
            case "user-service":
                return MultiPeakTrafficPattern.TrafficType.DIURNAL;
            case "order-service":
            case "payment-service":
                return MultiPeakTrafficPattern.TrafficType.SPIKY;
            case "product-service":
                return MultiPeakTrafficPattern.TrafficType.EVENT_DRIVEN;
            default:
                return MultiPeakTrafficPattern.TrafficType.DIURNAL;
        }
    }

    public List<TimeSeriesPoint> generateMultiPeakTimeSeries(String serviceId, int minutes) {
        MultiPeakTrafficPattern pattern = generateTrafficPattern(serviceId);
        return generateTimeSeries(pattern, minutes);
    }

    public List<TimeSeriesPoint> generateTimeSeries(MultiPeakTrafficPattern pattern, int minutes) {
        List<TimeSeriesPoint> series = new ArrayList<>();
        LocalDateTime startTime = LocalDateTime.now();

        activeBursts.putIfAbsent(pattern.getServiceId(), new ArrayList<>());
        List<MultiPeakTrafficPattern.BurstEvent> currentBursts = activeBursts.get(pattern.getServiceId());

        for (int i = 0; i < minutes; i++) {
            LocalDateTime timestamp = startTime.plusMinutes(i);

            double qps = calculateQpsAtTime(pattern, timestamp, currentBursts);

            double noise = (random.nextGaussian() * pattern.getVariance());
            qps = qps * (1 + noise);
            qps = Math.max(0, qps);

            double upperBound = qps * (1 + pattern.getVariance());
            double lowerBound = Math.max(0, qps * (1 - pattern.getVariance()));

            series.add(TimeSeriesPoint.builder()
                    .timestamp(timestamp)
                    .value(Math.round(qps * 100.0) / 100.0)
                    .upperBound(Math.round(upperBound * 100.0) / 100.0)
                    .lowerBound(Math.round(lowerBound * 100.0) / 100.0)
                    .build());
        }

        return series;
    }

    private double calculateQpsAtTime(MultiPeakTrafficPattern pattern,
                                       LocalDateTime timestamp,
                                       List<MultiPeakTrafficPattern.BurstEvent> bursts) {
        double qps = pattern.getBaselineQps();

        double hourOfDay = timestamp.getHour() + timestamp.getMinute() / 60.0;
        int dayOfWeek = timestamp.getDayOfWeek().getValue();

        for (MultiPeakTrafficPattern.PeriodicPeak peak : pattern.getPeriodicPeaks()) {
            if (peak.getDaysOfWeek().contains(dayOfWeek)) {
                double peakFactor = calculatePeakFactor(hourOfDay, peak);
                qps = Math.max(qps, pattern.getBaselineQps() * peakFactor);
            }
        }

        for (MultiPeakTrafficPattern.BurstEvent burst : pattern.getBurstEvents()) {
            double burstFactor = calculateBurstFactor(timestamp, burst);
            if (burstFactor > 1) {
                qps = Math.max(qps, pattern.getBaselineQps() * burstFactor);
            }
        }

        return qps;
    }

    private double calculatePeakFactor(double hourOfDay, MultiPeakTrafficPattern.PeriodicPeak peak) {
        double midHour = (peak.getStartHour() + peak.getEndHour()) / 2.0;
        double distance = Math.abs(hourOfDay - midHour);
        double halfWidth = peak.getWidth() / 2.0;

        if (distance <= halfWidth) {
            double normalizedDistance = distance / halfWidth;
            double gaussianFactor = Math.exp(-0.5 * normalizedDistance * normalizedDistance);
            return 1 + (peak.getIntensity() - 1) * gaussianFactor;
        }

        return 1.0;
    }

    private double calculateBurstFactor(LocalDateTime time, MultiPeakTrafficPattern.BurstEvent burst) {
        if (time.isBefore(burst.getStartTime())) {
            return 1.0;
        }

        LocalDateTime endTime = burst.getStartTime().plusMinutes(burst.getDurationMinutes());
        if (time.isAfter(endTime)) {
            return 1.0;
        }

        long secondsSinceStart = java.time.Duration.between(burst.getStartTime(), time).getSeconds();
        long totalSeconds = burst.getDurationMinutes() * 60;
        double progress = (double) secondsSinceStart / totalSeconds;

        double envelope;
        if (progress < 0.1) {
            envelope = progress / 0.1;
        } else if (progress > 0.9) {
            envelope = (1 - progress) / 0.1;
        } else {
            envelope = 1.0;
        }

        double oscillation = 0.7 + 0.3 * Math.sin(progress * Math.PI * 8);

        return 1 + (burst.getIntensity() - 1) * envelope * oscillation;
    }

    public double getCurrentQps(String serviceId) {
        MultiPeakTrafficPattern pattern = generateTrafficPattern(serviceId);
        List<MultiPeakTrafficPattern.BurstEvent> bursts = activeBursts.getOrDefault(serviceId, new ArrayList<>());
        return calculateQpsAtTime(pattern, LocalDateTime.now(), bursts);
    }

    public void triggerManualBurst(String serviceId, double intensity, int durationMinutes) {
        MultiPeakTrafficPattern.BurstEvent burst = MultiPeakTrafficPattern.BurstEvent.builder()
                .id("manual-" + UUID.randomUUID())
                .startTime(LocalDateTime.now())
                .durationMinutes(durationMinutes)
                .intensity(intensity)
                .type(MultiPeakTrafficPattern.BurstType.RANDOM_SPIKE)
                .description("手动触发的突发流量")
                .build();

        activeBursts.computeIfAbsent(serviceId, k -> new ArrayList<>()).add(burst);
    }

    public Map<String, Object> getTrafficPatternSummary(String serviceId) {
        MultiPeakTrafficPattern pattern = generateTrafficPattern(serviceId);
        Map<String, Object> summary = new HashMap<>();

        summary.put("serviceId", serviceId);
        summary.put("baselineQps", pattern.getBaselineQps());
        summary.put("trafficType", pattern.getTrafficType());
        summary.put("peakCount", pattern.getPeriodicPeaks().size());
        summary.put("burstCount", pattern.getBurstEvents().size());

        double maxIntensity = pattern.getPeriodicPeaks().stream()
                .mapToDouble(MultiPeakTrafficPattern.PeriodicPeak::getIntensity)
                .max()
                .orElse(1.0);
        summary.put("maxPeakIntensity", maxIntensity);

        double maxBurstIntensity = pattern.getBurstEvents().stream()
                .mapToDouble(MultiPeakTrafficPattern.BurstEvent::getIntensity)
                .max()
                .orElse(1.0);
        summary.put("maxBurstIntensity", maxBurstIntensity);

        return summary;
    }
}
