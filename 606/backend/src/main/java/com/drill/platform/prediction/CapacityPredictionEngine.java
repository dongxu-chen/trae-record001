package com.drill.platform.prediction;

import com.drill.platform.model.*;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Component
public class CapacityPredictionEngine {

    public CapacityPrediction predictCapacity(
            String targetSystem,
            List<DrillTask> historicalDrills,
            int predictionHorizonHours) {
        
        CapacityPrediction prediction = new CapacityPrediction();
        prediction.setId(UUID.randomUUID().toString());
        prediction.setTargetSystem(targetSystem);
        prediction.setPredictionTime(new Date());
        prediction.setPredictionHorizonHours(predictionHorizonHours);
        
        List<CapacityPrediction.CapacityDataPoint> historicalData = extractHistoricalData(historicalDrills);
        prediction.setHistoricalData(historicalData);
        
        calculateCurrentCapacity(prediction, historicalData);
        
        List<CapacityPrediction.CapacityDataPoint> predictedData = generatePredictionData(
                historicalData, predictionHorizonHours);
        prediction.setPredictedData(predictedData);
        
        calculatePredictions(prediction, historicalData, predictedData);
        
        assessRiskLevel(prediction);
        
        generateWarningsAndRecommendations(prediction);
        
        prediction.setConfidence(calculateConfidence(historicalDrills.size(), historicalData.size()));
        
        return prediction;
    }

    private List<CapacityPrediction.CapacityDataPoint> extractHistoricalData(List<DrillTask> drills) {
        return drills.stream()
                .filter(d -> d.getResult() != null && d.getResult().getRealtimeMetrics() != null)
                .flatMap(drill -> {
                    List<CapacityPrediction.CapacityDataPoint> points = new ArrayList<>();
                    List<SentinelMetric> metrics = drill.getResult().getRealtimeMetrics();
                    
                    for (int i = 0; i < metrics.size(); i++) {
                        SentinelMetric metric = metrics.get(i);
                        CapacityPrediction.CapacityDataPoint point = new CapacityPrediction.CapacityDataPoint();
                        
                        Calendar cal = Calendar.getInstance();
                        if (drill.getStartTime() != null) {
                            cal.setTime(drill.getStartTime());
                        }
                        cal.add(Calendar.SECOND, i);
                        point.setTimestamp(cal.getTime());
                        
                        point.setQps(metric.getQps());
                        point.setLatencyMs((double) metric.getResponseTimeMs());
                        point.setErrorRate(metric.getErrorRate());
                        
                        double qpsRatio = metric.getQps() / Math.max(1, drill.getTrafficProfile() != null 
                                ? drill.getTrafficProfile().getPeakQps() : 1000);
                        point.setCpuUsage(qpsRatio * 80 + new Random().nextDouble() * 10);
                        point.setMemoryUsage(50 + qpsRatio * 30 + new Random().nextDouble() * 10);
                        point.setThreadCount(50 + qpsRatio * 150);
                        
                        points.add(point);
                    }
                    return points.stream();
                })
                .sorted(Comparator.comparing(CapacityPrediction.CapacityDataPoint::getTimestamp))
                .collect(Collectors.toList());
    }

    private void calculateCurrentCapacity(
            CapacityPrediction prediction,
            List<CapacityPrediction.CapacityDataPoint> historicalData) {
        
        if (historicalData.isEmpty()) {
            prediction.setCurrentCapacity(100.0);
            prediction.setSafeCapacity(80.0);
            prediction.setMaxCapacity(150.0);
            prediction.setCapacityUtilization(50.0);
            return;
        }
        
        double maxQps = historicalData.stream()
                .mapToDouble(CapacityPrediction.CapacityDataPoint::getQps)
                .max()
                .orElse(100);
        
        double avgLatency = historicalData.stream()
                .mapToDouble(CapacityPrediction.CapacityDataPoint::getLatencyMs)
                .average()
                .orElse(100);
        
        double maxSafeQps = historicalData.stream()
                .filter(p -> p.getErrorRate() < 5 && p.getLatencyMs() < avgLatency * 2)
                .mapToDouble(CapacityPrediction.CapacityDataPoint::getQps)
                .max()
                .orElse(maxQps * 0.8);
        
        prediction.setCurrentCapacity(maxQps);
        prediction.setSafeCapacity(maxSafeQps);
        prediction.setMaxCapacity(maxQps * 1.2);
        prediction.setCapacityUtilization((maxQps / (maxQps * 1.5)) * 100);
    }

    private List<CapacityPrediction.CapacityDataPoint> generatePredictionData(
            List<CapacityPrediction.CapacityDataPoint> historicalData,
            int horizonHours) {
        
        List<CapacityPrediction.CapacityDataPoint> predictedData = new ArrayList<>();
        
        if (historicalData.isEmpty()) {
            return predictedData;
        }
        
        double trendSlope = calculateTrendSlope(historicalData);
        double noiseLevel = calculateNoiseLevel(historicalData);
        
        Date lastTimestamp = historicalData.get(historicalData.size() - 1).getTimestamp();
        
        int dataPoints = Math.min(horizonHours * 12, 168);
        
        for (int i = 1; i <= dataPoints; i++) {
            CapacityPrediction.CapacityDataPoint point = new CapacityPrediction.CapacityDataPoint();
            
            Calendar cal = Calendar.getInstance();
            cal.setTime(lastTimestamp);
            cal.add(Calendar.MINUTE, i * 5);
            point.setTimestamp(cal.getTime());
            
            double baseQps = historicalData.stream()
                    .mapToDouble(CapacityPrediction.CapacityDataPoint::getQps)
                    .average()
                    .orElse(100);
            
            double predictedQps = baseQps * (1 + trendSlope * i * 0.01) 
                    * (1 + Math.sin(i * 0.5) * 0.2)
                    + (new Random().nextDouble() - 0.5) * noiseLevel;
            
            point.setQps(Math.max(1, predictedQps));
            
            double loadFactor = predictedQps / baseQps;
            point.setLatencyMs(historicalData.stream()
                    .mapToDouble(CapacityPrediction.CapacityDataPoint::getLatencyMs)
                    .average().orElse(100) * (1 + loadFactor * 0.3));
            
            point.setErrorRate(Math.min(100, Math.max(0, (loadFactor - 1.2) * 20)));
            point.setCpuUsage(Math.min(100, 40 + loadFactor * 40));
            point.setMemoryUsage(Math.min(100, 50 + loadFactor * 30));
            point.setThreadCount(50 + loadFactor * 100);
            point.setPhase("PREDICTED");
            
            predictedData.add(point);
        }
        
        return predictedData;
    }

    private double calculateTrendSlope(List<CapacityPrediction.CapacityDataPoint> data) {
        if (data.size() < 2) {
            return 0;
        }
        
        int n = data.size();
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        
        for (int i = 0; i < n; i++) {
            sumX += i;
            sumY += data.get(i).getQps();
            sumXY += i * data.get(i).getQps();
            sumX2 += i * i;
        }
        
        return (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX) / 100;
    }

    private double calculateNoiseLevel(List<CapacityPrediction.CapacityDataPoint> data) {
        if (data.size() < 2) {
            return 10;
        }
        
        double avg = data.stream().mapToDouble(CapacityPrediction.CapacityDataPoint::getQps).average().orElse(0);
        double variance = data.stream()
                .mapToDouble(p -> Math.pow(p.getQps() - avg, 2))
                .average()
                .orElse(0);
        
        return Math.sqrt(variance);
    }

    private void calculatePredictions(
            CapacityPrediction prediction,
            List<CapacityPrediction.CapacityDataPoint> historicalData,
            List<CapacityPrediction.CapacityDataPoint> predictedData) {
        
        if (predictedData.isEmpty()) {
            prediction.setPredictedPeakQps(historicalData.stream()
                    .mapToDouble(CapacityPrediction.CapacityDataPoint::getQps)
                    .max().orElse(100));
            prediction.setPredictedPeakLatency(100.0);
            prediction.setPredictedErrorRate(1.0);
            return;
        }
        
        prediction.setPredictedPeakQps(predictedData.stream()
                .mapToDouble(CapacityPrediction.CapacityDataPoint::getQps)
                .max().orElse(100));
        prediction.setPredictedPeakLatency(predictedData.stream()
                .mapToDouble(CapacityPrediction.CapacityDataPoint::getLatencyMs)
                .max().orElse(100));
        prediction.setPredictedErrorRate(predictedData.stream()
                .mapToDouble(CapacityPrediction.CapacityDataPoint::getErrorRate)
                .average().orElse(1));
        
        Map<String, Object> model = new HashMap<>();
        model.put("trendSlope", calculateTrendSlope(historicalData));
        model.put("noiseLevel", calculateNoiseLevel(historicalData));
        model.put("dataPoints", historicalData.size());
        prediction.setPredictionModel(model);
    }

    private void assessRiskLevel(CapacityPrediction prediction) {
        double utilization = prediction.getCapacityUtilization();
        double predictedPeak = prediction.getPredictedPeakQps();
        double safeCapacity = prediction.getSafeCapacity();
        
        double overloadRatio = predictedPeak / safeCapacity;
        
        String riskLevel;
        if (overloadRatio < 0.7) {
            riskLevel = CapacityPrediction.RiskLevel.LOW.name();
        } else if (overloadRatio < 0.9) {
            riskLevel = CapacityPrediction.RiskLevel.MEDIUM.name();
        } else if (overloadRatio < 1.1) {
            riskLevel = CapacityPrediction.RiskLevel.HIGH.name();
        } else {
            riskLevel = CapacityPrediction.RiskLevel.CRITICAL.name();
        }
        
        prediction.setRiskLevel(riskLevel);
    }

    private void generateWarningsAndRecommendations(CapacityPrediction prediction) {
        List<String> warnings = new ArrayList<>();
        List<String> recommendations = new ArrayList<>();
        
        String riskLevel = prediction.getRiskLevel();
        
        if (CapacityPrediction.RiskLevel.CRITICAL.name().equals(riskLevel)) {
            warnings.add("预测流量将严重超出系统安全容量");
            recommendations.add("立即扩容或升级限流策略阈值");
            recommendations.add("考虑多可用区部署提升容错能力");
        } else if (CapacityPrediction.RiskLevel.HIGH.name().equals(riskLevel)) {
            warnings.add("预测流量接近系统安全容量上限");
            recommendations.add("建议上调限流阈值20-30%");
            recommendations.add("准备扩容预案，关注高峰期表现");
        } else if (CapacityPrediction.RiskLevel.MEDIUM.name().equals(riskLevel)) {
            warnings.add("系统利用率较高，需关注流量波动");
            recommendations.add("持续监控系统指标");
            recommendations.add("考虑优化热点接口性能");
        } else {
            recommendations.add("系统容量充足，运行状态良好");
        }
        
        if (prediction.getPredictedPeakLatency() > 500) {
            warnings.add("预测响应时间可能超过500ms");
            recommendations.add("排查慢SQL和第三方依赖");
        }
        
        if (prediction.getPredictedErrorRate() > 5) {
            warnings.add("预测错误率可能超过5%");
            recommendations.add("加强降级策略配置");
        }
        
        prediction.setWarnings(warnings);
        prediction.setRecommendations(recommendations);
    }

    private double calculateConfidence(int drillCount, int dataPoints) {
        double drillFactor = Math.min(drillCount / 10.0, 1.0);
        double dataFactor = Math.min(dataPoints / 100.0, 1.0);
        return 0.4 + drillFactor * 0.3 + dataFactor * 0.3;
    }

    public Map<String, Double> calculateWatermarkLevels(
            List<DrillTask> drills,
            double safetyFactor) {
        
        Map<String, Double> watermarks = new HashMap<>();
        
        if (drills.isEmpty()) {
            watermarks.put("lowWatermark", 100.0);
            watermarks.put("midWatermark", 200.0);
            watermarks.put("highWatermark", 300.0);
            watermarks.put("safeWatermark", 80.0);
            return watermarks;
        }
        
        double avgPeakQps = drills.stream()
                .filter(d -> d.getResult() != null)
                .mapToDouble(d -> d.getResult().getActualQps())
                .average()
                .orElse(100);
        
        watermarks.put("lowWatermark", avgPeakQps * 0.5 * safetyFactor);
        watermarks.put("midWatermark", avgPeakQps * 0.75 * safetyFactor);
        watermarks.put("highWatermark", avgPeakQps * safetyFactor);
        watermarks.put("safeWatermark", avgPeakQps * 0.8 * safetyFactor);
        
        return watermarks;
    }
}
