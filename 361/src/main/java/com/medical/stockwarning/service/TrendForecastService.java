package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.TrendForecastDTO;
import com.medical.stockwarning.entity.ConsumptionHistory;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.repository.ConsumptionHistoryRepository;
import com.medical.stockwarning.repository.MedicineRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.math3.stat.regression.SimpleRegression;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class TrendForecastService {

    private final ConsumptionHistoryRepository consumptionHistoryRepository;
    private final MedicineRepository medicineRepository;

    @Value("${app.forecast.history-days:365}")
    private int historyDays;

    @Value("${app.forecast.default-days:30}")
    private int defaultForecastDays;

    @Value("${app.forecast.seasonal-threshold:0.15}")
    private double seasonalThreshold;

    @Value("${app.forecast.confidence-level:0.95}")
    private double confidenceLevel;

    public TrendForecastDTO forecastMedicineDemand(Long medicineId, Long warehouseId, int forecastDays) {
        Medicine medicine = medicineRepository.findById(medicineId)
                .orElseThrow(() -> new IllegalArgumentException("Medicine not found: " + medicineId));

        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(historyDays);

        List<ConsumptionHistory> history;
        if (warehouseId != null) {
            history = consumptionHistoryRepository
                    .findByWarehouseIdAndMedicineIdAndConsumptionDateBetween(
                            warehouseId, medicineId, startDate, endDate);
        } else {
            history = consumptionHistoryRepository
                    .findByMedicineIdAndConsumptionDateBetween(medicineId, startDate, endDate);
        }

        if (history.isEmpty()) {
            log.warn("No consumption history for medicine={}, warehouse={}", medicineId, warehouseId);
            return createEmptyForecast(medicine, forecastDays);
        }

        Map<LocalDate, Double> dailyData = aggregateDailyData(history, startDate, endDate);

        double[] values = dailyData.values().stream().mapToDouble(Double::doubleValue).toArray();

        double mean = calculateMean(values);
        double stdDev = calculateStdDev(values, mean);

        SimpleRegression regression = calculateTrend(values);
        double trendSlope = regression.getSlope();
        String trendDirection = trendSlope > 0.5 ? "UP" : trendSlope < -0.5 ? "DOWN" : "STABLE";

        boolean isSeasonal = detectSeasonality(dailyData, mean);
        String seasonPattern = identifySeasonPattern(dailyData, mean);
        double seasonalFactor = calculateSeasonalFactor(dailyData, mean);

        List<TrendForecastDTO.DailyForecast> dailyForecasts = generateForecast(
                medicine, dailyData, trendSlope, seasonalFactor, mean, stdDev, forecastDays);

        BigDecimal totalForecasted = dailyForecasts.stream()
                .map(TrendForecastDTO.DailyForecast::getForecastedQuantity)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal peakDemand = dailyForecasts.stream()
                .map(TrendForecastDTO.DailyForecast::getForecastedQuantity)
                .max(BigDecimal::compareTo)
                .orElse(BigDecimal.ZERO);

        LocalDate peakDate = dailyForecasts.stream()
                .filter(d -> d.getForecastedQuantity().equals(peakDemand))
                .map(TrendForecastDTO.DailyForecast::getDate)
                .findFirst()
                .orElse(null);

        TrendForecastDTO result = TrendForecastDTO.builder()
                .medicineId(medicineId)
                .medicineName(medicine.getMedicineName())
                .medicineCode(medicine.getMedicineCode())
                .forecastStartDate(LocalDate.now().plusDays(1))
                .forecastEndDate(LocalDate.now().plusDays(forecastDays))
                .forecastDays(forecastDays)
                .dailyForecasts(dailyForecasts)
                .totalForecastedQuantity(totalForecasted)
                .averageDailyDemand(BigDecimal.valueOf(mean).setScale(2, RoundingMode.HALF_UP))
                .peakDailyDemand(peakDemand)
                .peakDate(peakDate)
                .isSeasonal(isSeasonal)
                .seasonPattern(seasonPattern)
                .seasonalFactor(BigDecimal.valueOf(seasonalFactor).setScale(4, RoundingMode.HALF_UP))
                .trendSlope(trendSlope)
                .trendDirection(trendDirection)
                .confidenceLevel(confidenceLevel)
                .build();

        log.info("Forecast for medicine {}: total={}, trend={}, seasonal={}, pattern={}",
                medicine.getMedicineName(), totalForecasted, trendDirection, isSeasonal, seasonPattern);

        return result;
    }

    public List<TrendForecastDTO> forecastAllMedicines(Long warehouseId, int forecastDays) {
        List<Medicine> medicines = medicineRepository.findByIsActive(1);
        List<TrendForecastDTO> forecasts = new ArrayList<>();

        for (Medicine medicine : medicines) {
            try {
                TrendForecastDTO forecast = forecastMedicineDemand(medicine.getId(), warehouseId, forecastDays);
                forecasts.add(forecast);
            } catch (Exception e) {
                log.error("Error forecasting medicine {}: {}", medicine.getMedicineName(), e.getMessage());
            }
        }

        return forecasts;
    }

    public List<TrendForecastDTO> getHighGrowthForecasts(Long warehouseId, int forecastDays) {
        return forecastAllMedicines(warehouseId, forecastDays).stream()
                .filter(f -> "UP".equals(f.getTrendDirection()))
                .sorted((a, b) -> Double.compare(b.getTrendSlope(), a.getTrendSlope()))
                .toList();
    }

    public List<TrendForecastDTO> getSeasonalForecasts(Long warehouseId, int forecastDays) {
        return forecastAllMedicines(warehouseId, forecastDays).stream()
                .filter(TrendForecastDTO::getIsSeasonal)
                .toList();
    }

    public List<TrendForecastDTO> getPeakSeasonForecasts(Long warehouseId, int forecastDays) {
        LocalDate today = LocalDate.now();
        String currentSeason = getCurrentSeason(today);

        return forecastAllMedicines(warehouseId, forecastDays).stream()
                .filter(f -> currentSeason.equals(f.getSeasonPattern()))
                .filter(f -> f.getIsSeasonal())
                .sorted((a, b) -> b.getPeakDailyDemand().compareTo(a.getPeakDailyDemand()))
                .toList();
    }

    private Map<LocalDate, Double> aggregateDailyData(
            List<ConsumptionHistory> history, LocalDate startDate, LocalDate endDate) {

        Map<LocalDate, Double> dailyData = new TreeMap<>();
        for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
            dailyData.put(date, 0.0);
        }

        for (ConsumptionHistory record : history) {
            dailyData.merge(record.getConsumptionDate(),
                    (double) record.getQuantity(), Double::sum);
        }

        return dailyData;
    }

    private double calculateMean(double[] values) {
        if (values.length == 0) return 0;
        double sum = 0;
        for (double v : values) sum += v;
        return sum / values.length;
    }

    private double calculateStdDev(double[] values, double mean) {
        if (values.length < 2) return 0;
        double sumSquaredDiff = 0;
        for (double v : values) {
            sumSquaredDiff += (v - mean) * (v - mean);
        }
        return Math.sqrt(sumSquaredDiff / (values.length - 1));
    }

    private SimpleRegression calculateTrend(double[] values) {
        SimpleRegression regression = new SimpleRegression();
        for (int i = 0; i < values.length; i++) {
            regression.addData(i, values[i]);
        }
        return regression;
    }

    private boolean detectSeasonality(Map<LocalDate, Double> dailyData, double mean) {
        if (mean == 0) return false;

        Map<Integer, List<Double>> monthGroups = new HashMap<>();
        for (Map.Entry<LocalDate, Double> entry : dailyData.entrySet()) {
            int month = entry.getKey().getMonthValue();
            monthGroups.computeIfAbsent(month, k -> new ArrayList<>()).add(entry.getValue());
        }

        double maxMonthMean = 0;
        double minMonthMean = Double.MAX_VALUE;

        for (List<Double> monthValues : monthGroups.values()) {
            if (monthValues.isEmpty()) continue;
            double monthMean = monthValues.stream().mapToDouble(Double::doubleValue).average().orElse(0);
            maxMonthMean = Math.max(maxMonthMean, monthMean);
            minMonthMean = Math.min(minMonthMean, monthMean);
        }

        double variation = (maxMonthMean - minMonthMean) / mean;
        return variation > seasonalThreshold;
    }

    private String identifySeasonPattern(Map<LocalDate, Double> dailyData, double mean) {
        Map<Integer, List<Double>> monthGroups = new HashMap<>();
        for (Map.Entry<LocalDate, Double> entry : dailyData.entrySet()) {
            int month = entry.getKey().getMonthValue();
            monthGroups.computeIfAbsent(month, k -> new ArrayList<>()).add(entry.getValue());
        }

        int peakMonth = 0;
        double peakMean = 0;

        for (Map.Entry<Integer, List<Double>> entry : monthGroups.entrySet()) {
            if (entry.getValue().isEmpty()) continue;
            double monthMean = entry.getValue().stream().mapToDouble(Double::doubleValue).average().orElse(0);
            if (monthMean > peakMean) {
                peakMean = monthMean;
                peakMonth = entry.getKey();
            }
        }

        if (peakMonth >= 3 && peakMonth <= 5) return "SPRING";
        if (peakMonth >= 6 && peakMonth <= 8) return "SUMMER";
        if (peakMonth >= 9 && peakMonth <= 11) return "AUTUMN";
        return "WINTER";
    }

    private double calculateSeasonalFactor(Map<LocalDate, Double> dailyData, double mean) {
        if (mean == 0) return 0;

        Map<String, List<Double>> seasonGroups = new HashMap<>();
        seasonGroups.put("SPRING", new ArrayList<>());
        seasonGroups.put("SUMMER", new ArrayList<>());
        seasonGroups.put("AUTUMN", new ArrayList<>());
        seasonGroups.put("WINTER", new ArrayList<>());

        for (Map.Entry<LocalDate, Double> entry : dailyData.entrySet()) {
            int month = entry.getKey().getMonthValue();
            String season = month >= 3 && month <= 5 ? "SPRING" :
                    month >= 6 && month <= 8 ? "SUMMER" :
                            month >= 9 && month <= 11 ? "AUTUMN" : "WINTER";
            seasonGroups.get(season).add(entry.getValue());
        }

        double maxSeasonMean = 0;
        double minSeasonMean = Double.MAX_VALUE;

        for (List<Double> seasonValues : seasonGroups.values()) {
            if (seasonValues.isEmpty()) continue;
            double seasonMean = seasonValues.stream().mapToDouble(Double::doubleValue).average().orElse(0);
            maxSeasonMean = Math.max(maxSeasonMean, seasonMean);
            minSeasonMean = Math.min(minSeasonMean, seasonMean);
        }

        if (mean == 0) return 0;
        return (maxSeasonMean - minSeasonMean) / mean;
    }

    private List<TrendForecastDTO.DailyForecast> generateForecast(
            Medicine medicine, Map<LocalDate, Double> historicalData,
            double trendSlope, double seasonalFactor, double mean, double stdDev, int forecastDays) {

        List<TrendForecastDTO.DailyForecast> forecasts = new ArrayList<>();
        LocalDate startDate = LocalDate.now().plusDays(1);

        double zScore = 1.96;

        Map<Integer, Double> monthlySeasonIndices = calculateMonthlySeasonIndices(historicalData);

        for (int i = 0; i < forecastDays; i++) {
            LocalDate forecastDate = startDate.plusDays(i);
            int month = forecastDate.getMonthValue();

            double baseForecast = mean + trendSlope * (historicalData.size() + i);
            double seasonIndex = monthlySeasonIndices.getOrDefault(month, 1.0);
            double adjustedForecast = baseForecast * seasonIndex;

            adjustedForecast = Math.max(adjustedForecast, 0);

            double marginOfError = zScore * stdDev;
            double lowerBound = Math.max(adjustedForecast - marginOfError, 0);
            double upperBound = adjustedForecast + marginOfError;

            String seasonTag = getCurrentSeason(forecastDate);

            forecasts.add(TrendForecastDTO.DailyForecast.builder()
                    .date(forecastDate)
                    .forecastedQuantity(BigDecimal.valueOf(adjustedForecast).setScale(2, RoundingMode.HALF_UP))
                    .lowerBound(BigDecimal.valueOf(lowerBound).setScale(2, RoundingMode.HALF_UP))
                    .upperBound(BigDecimal.valueOf(upperBound).setScale(2, RoundingMode.HALF_UP))
                    .seasonTag(seasonTag)
                    .build());
        }

        return forecasts;
    }

    private Map<Integer, Double> calculateMonthlySeasonIndices(Map<LocalDate, Double> historicalData) {
        Map<Integer, List<Double>> monthValues = new HashMap<>();

        for (Map.Entry<LocalDate, Double> entry : historicalData.entrySet()) {
            int month = entry.getKey().getMonthValue();
            monthValues.computeIfAbsent(month, k -> new ArrayList<>()).add(entry.getValue());
        }

        double overallMean = historicalData.values().stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(1.0);

        Map<Integer, Double> indices = new HashMap<>();
        for (Map.Entry<Integer, List<Double>> entry : monthValues.entrySet()) {
            double monthMean = entry.getValue().stream()
                    .mapToDouble(Double::doubleValue)
                    .average()
                    .orElse(overallMean);
            indices.put(entry.getKey(), overallMean > 0 ? monthMean / overallMean : 1.0);
        }

        return indices;
    }

    private String getCurrentSeason(LocalDate date) {
        int month = date.getMonthValue();
        if (month >= 3 && month <= 5) return "SPRING";
        if (month >= 6 && month <= 8) return "SUMMER";
        if (month >= 9 && month <= 11) return "AUTUMN";
        return "WINTER";
    }

    private TrendForecastDTO createEmptyForecast(Medicine medicine, int forecastDays) {
        List<TrendForecastDTO.DailyForecast> emptyForecasts = new ArrayList<>();
        LocalDate startDate = LocalDate.now().plusDays(1);

        for (int i = 0; i < forecastDays; i++) {
            emptyForecasts.add(TrendForecastDTO.DailyForecast.builder()
                    .date(startDate.plusDays(i))
                    .forecastedQuantity(BigDecimal.ZERO)
                    .lowerBound(BigDecimal.ZERO)
                    .upperBound(BigDecimal.ZERO)
                    .seasonTag(getCurrentSeason(startDate.plusDays(i)))
                    .build());
        }

        return TrendForecastDTO.builder()
                .medicineId(medicine.getId())
                .medicineName(medicine.getMedicineName())
                .medicineCode(medicine.getMedicineCode())
                .forecastStartDate(startDate)
                .forecastEndDate(startDate.plusDays(forecastDays - 1))
                .forecastDays(forecastDays)
                .dailyForecasts(emptyForecasts)
                .totalForecastedQuantity(BigDecimal.ZERO)
                .averageDailyDemand(BigDecimal.ZERO)
                .peakDailyDemand(BigDecimal.ZERO)
                .isSeasonal(false)
                .seasonPattern("UNKNOWN")
                .seasonalFactor(BigDecimal.ZERO)
                .trendSlope(0.0)
                .trendDirection("STABLE")
                .confidenceLevel(confidenceLevel)
                .build();
    }

    public List<Map<String, Object>> getTrendSummary() {
        List<Medicine> medicines = medicineRepository.findByIsActive(1);
        List<Map<String, Object>> summary = new ArrayList<>();

        for (Medicine medicine : medicines) {
            Map<String, Object> item = new HashMap<>();
            item.put("medicineId", medicine.getId());
            item.put("medicineName", medicine.getMedicineName());

            try {
                TrendForecastDTO forecast = forecastMedicineDemand(medicine.getId(), null, 30);
                item.put("trendDirection", forecast.getTrendDirection());
                item.put("trendSlope", forecast.getTrendSlope());
                item.put("isSeasonal", forecast.getIsSeasonal());
                item.put("seasonPattern", forecast.getSeasonPattern());
                item.put("totalForecast", forecast.getTotalForecastedQuantity());
            } catch (Exception e) {
                item.put("error", e.getMessage());
            }

            summary.add(item);
        }

        return summary;
    }
}
