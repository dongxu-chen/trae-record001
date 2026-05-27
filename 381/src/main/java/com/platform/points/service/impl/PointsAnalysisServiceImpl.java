package com.platform.points.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.platform.points.entity.PointsRecord;
import com.platform.points.entity.PointsLevelConfig;
import com.platform.points.entity.UserPoints;
import com.platform.points.enums.PointsTypeEnum;
import com.platform.points.enums.PointsSourceEnum;
import com.platform.points.mapper.PointsRecordMapper;
import com.platform.points.mapper.PointsLevelConfigMapper;
import com.platform.points.mapper.UserPointsMapper;
import com.platform.points.service.PointsAnalysisService;
import com.platform.points.vo.PointsLeverageVO;
import com.platform.points.vo.PointsPredictionVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class PointsAnalysisServiceImpl implements PointsAnalysisService {

    @Autowired
    private UserPointsMapper userPointsMapper;

    @Autowired
    private PointsRecordMapper pointsRecordMapper;

    @Autowired
    private PointsLevelConfigMapper levelConfigMapper;

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final double GMV_POINTS_RATIO = 100.0;

    @Override
    public PointsPredictionVO predictPointsGrowth(Long userId, int days) {
        LambdaQueryWrapper<UserPoints> pointsWrapper = new LambdaQueryWrapper<>();
        pointsWrapper.eq(UserPoints::getUserId, userId);
        UserPoints userPoints = userPointsMapper.selectOne(pointsWrapper);

        if (userPoints == null) {
            return createEmptyPrediction(userId);
        }

        PointsPredictionVO vo = new PointsPredictionVO();
        vo.setUserId(userId);
        vo.setCurrentPoints(userPoints.getTotalPoints());

        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(30);

        LambdaQueryWrapper<PointsRecord> recordWrapper = new LambdaQueryWrapper<>();
        recordWrapper.eq(PointsRecord::getUserId, userId)
                .eq(PointsRecord::getPointsType, PointsTypeEnum.GRANT.getCode())
                .ge(PointsRecord::getCreateTime, startDate.atStartOfDay())
                .le(PointsRecord::getCreateTime, endDate.atTime(23, 59, 59));
        List<PointsRecord> records = pointsRecordMapper.selectList(recordWrapper);

        Map<String, Integer> dailyPoints = calculateDailyPoints(records, startDate, endDate);

        double[] growthRates = calculateGrowthRates(dailyPoints);
        double avgGrowthRate = Arrays.stream(growthRates).average().orElse(0.05);
        vo.setMonthlyGrowthRate(avgGrowthRate * 100);

        List<PointsPredictionVO.PredictionPoint> predictions = generatePredictions(
                userPoints.getTotalPoints(), avgGrowthRate, days, dailyPoints);
        vo.setPredictionPoints(predictions);

        calculateLevelUpInfo(vo, userPoints.getTotalPoints(), avgGrowthRate);

        return vo;
    }

    @Override
    public PointsLeverageVO analyzePointsLeverage(String startDateStr, String endDateStr) {
        LocalDate startDate = LocalDate.parse(startDateStr, DATE_FORMATTER);
        LocalDate endDate = LocalDate.parse(endDateStr, DATE_FORMATTER);

        PointsLeverageVO vo = new PointsLeverageVO();
        vo.setStartDate(startDateStr);
        vo.setEndDate(endDateStr);

        LambdaQueryWrapper<PointsRecord> recordWrapper = new LambdaQueryWrapper<>();
        recordWrapper.ge(PointsRecord::getCreateTime, startDate.atStartOfDay())
                .le(PointsRecord::getCreateTime, endDate.atTime(23, 59, 59));
        List<PointsRecord> records = pointsRecordMapper.selectList(recordWrapper);

        int totalGranted = records.stream()
                .filter(r -> PointsTypeEnum.GRANT.getCode().equals(r.getPointsType()))
                .mapToInt(PointsRecord::getPoints)
                .sum();
        int totalConsumed = records.stream()
                .filter(r -> PointsTypeEnum.DEDUCT.getCode().equals(r.getPointsType()))
                .mapToInt(PointsRecord::getPoints)
                .sum();

        vo.setTotalPointsGranted(totalGranted);
        vo.setTotalPointsConsumed(totalConsumed);
        vo.setPointsUtilizationRate(totalGranted > 0 ? (double) totalConsumed / totalGranted * 100 : 0.0);

        double estimatedGMV = totalConsumed / GMV_POINTS_RATIO * 1000;
        vo.setEstimatedGMV(estimatedGMV);
        vo.setPointsLeverageRatio(totalConsumed > 0 ? estimatedGMV / totalConsumed : 0);
        vo.setGmvIncrementRate(calculateGMVIncrement(records, startDate, endDate));

        List<PointsLeverageVO.DailyData> dailyData = generateDailyAnalysis(records, startDate, endDate);
        vo.setDailyData(dailyData);

        vo.setSourceContribution(calculateSourceContribution(records));

        Set<Long> uniqueUsers = records.stream().map(PointsRecord::getUserId).collect(Collectors.toSet());
        vo.setActiveUsers(uniqueUsers.size());
        vo.setAvgPointsPerUser(uniqueUsers.size() > 0 ? (double) totalGranted / uniqueUsers.size() : 0.0);

        return vo;
    }

    private PointsPredictionVO createEmptyPrediction(Long userId) {
        PointsPredictionVO vo = new PointsPredictionVO();
        vo.setUserId(userId);
        vo.setCurrentPoints(0);
        vo.setMonthlyGrowthRate(0.0);
        vo.setPredictionPoints(new ArrayList<>());
        return vo;
    }

    private Map<String, Integer> calculateDailyPoints(List<PointsRecord> records, LocalDate startDate, LocalDate endDate) {
        Map<String, Integer> dailyPoints = new LinkedHashMap<>();
        for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
            dailyPoints.put(date.format(DATE_FORMATTER), 0);
        }

        for (PointsRecord record : records) {
            LocalDate recordDate = record.getCreateTime().toLocalDate();
            String dateKey = recordDate.format(DATE_FORMATTER);
            if (dailyPoints.containsKey(dateKey)) {
                dailyPoints.put(dateKey, dailyPoints.get(dateKey) + record.getPoints());
            }
        }

        return dailyPoints;
    }

    private double[] calculateGrowthRates(Map<String, Integer> dailyPoints) {
        List<Integer> values = new ArrayList<>(dailyPoints.values());
        if (values.size() < 2) {
            return new double[]{0.05};
        }

        List<Double> rates = new ArrayList<>();
        for (int i = 1; i < values.size(); i++) {
            if (values.get(i - 1) > 0) {
                double rate = (double) (values.get(i) - values.get(i - 1)) / values.get(i - 1);
                if (Math.abs(rate) < 1.0) {
                    rates.add(rate);
                }
            }
        }

        return rates.stream().mapToDouble(Double::doubleValue).toArray();
    }

    private List<PointsPredictionVO.PredictionPoint> generatePredictions(
            int currentPoints, double growthRate, int days, Map<String, Integer> history) {

        List<PointsPredictionVO.PredictionPoint> predictions = new ArrayList<>();
        LocalDate today = LocalDate.now();

        List<Integer> historyValues = new ArrayList<>(history.values());
        int avgDailyPoints = historyValues.stream().mapToInt(Integer::intValue).average().orElse(10);
        if (avgDailyPoints == 0) avgDailyPoints = 10;

        int points = currentPoints;
        double volatility = calculateVolatility(historyValues);

        for (int i = 1; i <= days; i++) {
            LocalDate predictionDate = today.plusDays(i);
            double dailyGrowth = avgDailyPoints * (1 + growthRate * (i / 30.0));
            dailyGrowth = dailyGrowth * (0.9 + Math.random() * 0.2);
            points += (int) dailyGrowth;

            PointsPredictionVO.PredictionPoint point = new PointsPredictionVO.PredictionPoint();
            point.setDate(predictionDate.format(DATE_FORMATTER));
            point.setPredictedPoints(points);
            point.setLowerBound((int) (points * (1 - volatility)));
            point.setUpperBound((int) (points * (1 + volatility)));

            predictions.add(point);
        }

        return predictions;
    }

    private double calculateVolatility(List<Integer> values) {
        if (values.size() < 2) return 0.1;
        double mean = values.stream().mapToInt(Integer::intValue).average().orElse(0);
        if (mean == 0) return 0.1;
        double variance = values.stream().mapToDouble(v -> Math.pow(v - mean, 2)).average().orElse(0);
        return Math.min(0.2, Math.sqrt(variance) / mean);
    }

    private void calculateLevelUpInfo(PointsPredictionVO vo, int currentPoints, double growthRate) {
        List<PointsLevelConfig> levels = levelConfigMapper.selectAllActiveLevels();
        if (levels.isEmpty()) return;

        PointsLevelConfig currentLevel = levels.stream()
                .filter(l -> l.getMinPoints() <= currentPoints && l.getMaxPoints() > currentPoints)
                .findFirst().orElse(levels.get(0));

        PointsLevelConfig nextLevel = levels.stream()
                .filter(l -> l.getLevelOrder() > currentLevel.getLevelOrder())
                .findFirst().orElse(null);

        if (nextLevel != null) {
            vo.setNextLevelName(nextLevel.getLevelName());
            int pointsToNext = nextLevel.getMinPoints() - currentPoints;
            vo.setPointsToNextLevel(pointsToNext);

            double avgDailyGrowth = Math.max(10, currentPoints * growthRate / 30);
            int estimatedDays = (int) Math.ceil(pointsToNext / avgDailyGrowth);
            vo.setEstimatedDaysToLevelUp(estimatedDays);

            if (estimatedDays < 3650) {
                vo.setEstimatedLevelUpDate(LocalDate.now().plusDays(estimatedDays).format(DATE_FORMATTER));
            } else {
                vo.setEstimatedLevelUpDate("暂无预计");
            }
        } else {
            vo.setNextLevelName("已达最高等级");
            vo.setPointsToNextLevel(0);
            vo.setEstimatedDaysToLevelUp(0);
            vo.setEstimatedLevelUpDate("-");
        }
    }

    private List<PointsLeverageVO.DailyData> generateDailyAnalysis(
            List<PointsRecord> records, LocalDate startDate, LocalDate endDate) {

        List<PointsLeverageVO.DailyData> dailyDataList = new ArrayList<>();

        for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
            LocalDate finalDate = date;
            List<PointsRecord> dailyRecords = records.stream()
                    .filter(r -> r.getCreateTime().toLocalDate().equals(finalDate))
                    .collect(Collectors.toList());

            int granted = dailyRecords.stream()
                    .filter(r -> PointsTypeEnum.GRANT.getCode().equals(r.getPointsType()))
                    .mapToInt(PointsRecord::getPoints)
                    .sum();
            int consumed = dailyRecords.stream()
                    .filter(r -> PointsTypeEnum.DEDUCT.getCode().equals(r.getPointsType()))
                    .mapToInt(PointsRecord::getPoints)
                    .sum();
            long userCount = dailyRecords.stream().map(PointsRecord::getUserId).distinct().count();

            PointsLeverageVO.DailyData data = new PointsLeverageVO.DailyData();
            data.setDate(date.format(DATE_FORMATTER));
            data.setPointsGranted(granted);
            data.setPointsConsumed(consumed);
            data.setEstimatedGMV(consumed / GMV_POINTS_RATIO * 1000);
            data.setUserCount(userCount);

            dailyDataList.add(data);
        }

        return dailyDataList;
    }

    private Map<String, Double> calculateSourceContribution(List<PointsRecord> records) {
        Map<String, Double> contribution = new LinkedHashMap<>();

        Map<Integer, Integer> sourceTotal = records.stream()
                .filter(r -> PointsTypeEnum.GRANT.getCode().equals(r.getPointsType()))
                .collect(Collectors.groupingBy(
                        PointsRecord::getPointsSource,
                        Collectors.summingInt(PointsRecord::getPoints)
                ));

        int total = sourceTotal.values().stream().mapToInt(Integer::intValue).sum();

        for (PointsSourceEnum source : PointsSourceEnum.values()) {
            int points = sourceTotal.getOrDefault(source.getCode(), 0);
            contribution.put(source.getDesc(), total > 0 ?
                    BigDecimal.valueOf(points * 100.0 / total)
                            .setScale(2, RoundingMode.HALF_UP).doubleValue() : 0.0);
        }

        return contribution;
    }

    private double calculateGMVIncrement(List<PointsRecord> records, LocalDate startDate, LocalDate endDate) {
        long periodDays = ChronoUnit.DAYS.between(startDate, endDate) + 1;
        LocalDate previousStart = startDate.minusDays(periodDays);

        int currentConsumed = records.stream()
                .filter(r -> PointsTypeEnum.DEDUCT.getCode().equals(r.getPointsType()))
                .mapToInt(PointsRecord::getPoints)
                .sum();

        LambdaQueryWrapper<PointsRecord> prevWrapper = new LambdaQueryWrapper<>();
        prevWrapper.ge(PointsRecord::getCreateTime, previousStart.atStartOfDay())
                .lt(PointsRecord::getCreateTime, startDate.atStartOfDay());
        List<PointsRecord> previousRecords = pointsRecordMapper.selectList(prevWrapper);

        int previousConsumed = previousRecords.stream()
                .filter(r -> PointsTypeEnum.DEDUCT.getCode().equals(r.getPointsType()))
                .mapToInt(PointsRecord::getPoints)
                .sum();

        if (previousConsumed == 0) return 0.0;
        return (double) (currentConsumed - previousConsumed) / previousConsumed * 100;
    }
}
