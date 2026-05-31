package com.checkin.service;

import com.checkin.entity.*;
import com.checkin.repository.*;
import com.checkin.util.DateUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.*;
import java.time.temporal.TemporalAdjusters;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class AnalysisService {

    @Autowired
    private CheckinAnalysisRepository analysisRepository;

    @Autowired
    private CheckinRecordRepository checkinRecordRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private CheckinStatsRepository statsRepository;

    @Scheduled(cron = "0 0 2 * * *")
    @Transactional
    public void generateDailyAnalysis() {
        LocalDate today = DateUtils.getUtcToday();
        generateAnalysis("DAILY", today);
        generateAnalysis("WEEKLY", today);
        generateAnalysis("MONTHLY", today);
    }

    @Transactional
    public CheckinAnalysis generateAnalysis(String periodType, LocalDate date) {
        LocalDate startDate = DateUtils.getPeriodStartUtc(periodType, date);
        LocalDate endDate = DateUtils.getPeriodEndUtc(periodType, date);

        CheckinAnalysis analysis = analysisRepository
                .findByPeriodTypeAndAnalysisDate(periodType, date)
                .orElseGet(() -> {
                    CheckinAnalysis newAnalysis = new CheckinAnalysis();
                    newAnalysis.setPeriodType(periodType);
                    newAnalysis.setAnalysisDate(date);
                    return newAnalysis;
                });

        long totalUsers = userRepository.count();
        analysis.setTotalUsers(totalUsers);

        LocalDate analysisEndDate = date.isBefore(endDate) ? date : endDate;
        long checkedInUsers = countUniqueCheckinUsers(periodType, startDate, analysisEndDate);
        analysis.setCheckedInUsers(checkedInUsers);

        double checkinRate = totalUsers > 0 ? (checkedInUsers * 100.0 / totalUsers) : 0;
        analysis.setCheckinRate(Math.round(checkinRate * 100) / 100.0);

        Map<String, Object> continuousStats = calculateContinuousStats(periodType, startDate, analysisEndDate);
        analysis.setMaxContinuousDays((Integer) continuousStats.get("max"));
        analysis.setAvgContinuousDays((Integer) continuousStats.get("avg"));

        Map<String, Object> churnAnalysis = analyzeChurnPoints(periodType, startDate, analysisEndDate);
        analysis.setChurnDay((Integer) churnAnalysis.get("churnDay"));
        analysis.setChurnRate((Double) churnAnalysis.get("churnRate"));

        long newUsers = countNewUsers(startDate, analysisEndDate);
        analysis.setNewUsers(newUsers);

        long lostUsers = countLostUsers(periodType, startDate, analysisEndDate);
        analysis.setLostUsers(lostUsers);

        long recheckCount = countRechecks(startDate, analysisEndDate);
        analysis.setRecheckCount(recheckCount);

        return analysisRepository.save(analysis);
    }

    public Map<String, Object> getAnalysis(String periodType, LocalDate startDate, LocalDate endDate) {
        Map<String, Object> result = new HashMap<>();
        
        List<CheckinAnalysis> analyses = analysisRepository
                .findByPeriodTypeAndAnalysisDateBetweenOrderByAnalysisDateAsc(
                        periodType, startDate, endDate);
        
        result.put("rawData", analyses);
        
        if (!analyses.isEmpty()) {
            double avgCheckinRate = analyses.stream()
                    .mapToDouble(a -> a.getCheckinRate() != null ? a.getCheckinRate() : 0)
                    .average()
                    .orElse(0);
            result.put("avgCheckinRate", Math.round(avgCheckinRate * 100) / 100.0);
            
            long totalCheckins = analyses.stream()
                    .mapToLong(a -> a.getCheckedInUsers() != null ? a.getCheckedInUsers() : 0)
                    .sum();
            result.put("totalCheckins", totalCheckins);
            
            int maxContinuous = analyses.stream()
                    .mapToInt(a -> a.getMaxContinuousDays() != null ? a.getMaxContinuousDays() : 0)
                    .max()
                    .orElse(0);
            result.put("maxContinuousDays", maxContinuous);
            
            double avgChurnRate = analyses.stream()
                    .mapToDouble(a -> a.getChurnRate() != null ? a.getChurnRate() : 0)
                    .average()
                    .orElse(0);
            result.put("avgChurnRate", Math.round(avgChurnRate * 100) / 100.0);
            
            long totalNewUsers = analyses.stream()
                    .mapToLong(a -> a.getNewUsers() != null ? a.getNewUsers() : 0)
                    .sum();
            result.put("totalNewUsers", totalNewUsers);
            
            long totalLostUsers = analyses.stream()
                    .mapToLong(a -> a.getLostUsers() != null ? a.getLostUsers() : 0)
                    .sum();
            result.put("totalLostUsers", totalLostUsers);
        }
        
        Map<String, Object> churnDetail = analyzeChurnPoints(periodType, startDate, endDate);
        result.put("churnAnalysis", churnDetail);
        
        result.put("trendData", generateTrendData(analyses));
        
        return result;
    }

    public Map<String, Object> getUserAnalysis(Long userId, String periodType) {
        Map<String, Object> result = new HashMap<>();
        LocalDate today = DateUtils.getUtcToday();
        LocalDate startDate = today.minusMonths(1);
        
        List<CheckinRecord> records = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(userId, periodType, startDate, today);
        
        result.put("totalCheckins", records.size());
        
        long recheckCount = records.stream()
                .filter(CheckinRecord::getIsRechecked)
                .count();
        result.put("recheckCount", recheckCount);
        
        int maxContinuous = calculateMaxContinuousForUser(records);
        result.put("maxContinuousDays", maxContinuous);
        
        double avgPerWeek = calculateAvgPerWeek(records, startDate, today);
        result.put("avgCheckinsPerWeek", Math.round(avgPerWeek * 10) / 10.0);
        
        Map<Integer, Long> weekdayDistribution = analyzeWeekdayDistribution(records);
        result.put("weekdayDistribution", weekdayDistribution);
        
        Map<String, Object> streakAnalysis = analyzeUserStreaks(userId, periodType, records);
        result.put("streakAnalysis", streakAnalysis);
        
        result.put("checkinRate", calculateUserCheckinRate(userId, periodType, startDate, today));
        
        return result;
    }

    private long countUniqueCheckinUsers(String periodType, LocalDate startDate, LocalDate endDate) {
        List<CheckinRecord> records = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(0L, periodType, startDate, endDate);
        
        return records.stream()
                .map(CheckinRecord::getUserId)
                .distinct()
                .count();
    }

    private Map<String, Object> calculateContinuousStats(String periodType, LocalDate startDate, LocalDate endDate) {
        Map<String, Object> result = new HashMap<>();
        
        List<CheckinStats> allStats = statsRepository.findAll();
        List<Integer> continuousDaysList = allStats.stream()
                .filter(s -> periodType.equals(s.getPeriodType()))
                .map(CheckinStats::getContinuousDays)
                .filter(d -> d != null && d > 0)
                .collect(Collectors.toList());
        
        if (continuousDaysList.isEmpty()) {
            result.put("max", 0);
            result.put("avg", 0);
            return result;
        }
        
        int max = continuousDaysList.stream().mapToInt(Integer::intValue).max().orElse(0);
        double avg = continuousDaysList.stream().mapToInt(Integer::intValue).average().orElse(0);
        
        result.put("max", max);
        result.put("avg", (int) Math.round(avg));
        
        return result;
    }

    private Map<String, Object> analyzeChurnPoints(String periodType, LocalDate startDate, LocalDate endDate) {
        Map<String, Object> result = new HashMap<>();
        
        Map<Integer, Long> dayDistribution = new HashMap<>();
        Map<Integer, Long> churnAtDay = new HashMap<>();
        
        List<CheckinRecord> allRecords = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(0L, periodType, startDate, endDate);
        
        Map<Long, List<LocalDate>> userCheckinDates = allRecords.stream()
                .collect(Collectors.groupingBy(
                        CheckinRecord::getUserId,
                        Collectors.mapping(CheckinRecord::getCheckinDate, Collectors.toList())
                ));
        
        for (Map.Entry<Long, List<LocalDate>> entry : userCheckinDates.entrySet()) {
            List<LocalDate> dates = entry.getValue().stream()
                    .sorted()
                    .collect(Collectors.toList());
            
            int currentStreak = 0;
            LocalDate lastDate = null;
            
            for (LocalDate date : dates) {
                if (lastDate == null || DateUtils.daysBetweenUtc(lastDate, date) == 1) {
                    currentStreak++;
                } else {
                    dayDistribution.merge(currentStreak, 1L, Long::sum);
                    if (currentStreak > 0) {
                        churnAtDay.merge(currentStreak + 1, 1L, Long::sum);
                    }
                    currentStreak = 1;
                }
                lastDate = date;
            }
            
            if (currentStreak > 0) {
                dayDistribution.merge(currentStreak, 1L, Long::sum);
            }
        }
        
        int maxDay = 0;
        long maxChurn = 0;
        for (Map.Entry<Integer, Long> entry : churnAtDay.entrySet()) {
            if (entry.getValue() > maxChurn && entry.getKey() <= 30) {
                maxChurn = entry.getValue();
                maxDay = entry.getKey();
            }
        }
        
        long totalStreaks = dayDistribution.values().stream().mapToLong(Long::longValue).sum();
        double churnRate = totalStreaks > 0 ? (maxChurn * 100.0 / totalStreaks) : 0;
        
        result.put("churnDay", maxDay);
        result.put("churnCount", maxChurn);
        result.put("churnRate", Math.round(churnRate * 100) / 100.0);
        result.put("dayDistribution", dayDistribution);
        result.put("churnDistribution", churnAtDay);
        
        List<Map<String, Object>> riskPoints = new ArrayList<>();
        for (int i = 1; i <= 14; i++) {
            long churn = churnAtDay.getOrDefault(i, 0L);
            if (churn > 0) {
                Map<String, Object> point = new HashMap<>();
                point.put("day", i);
                point.put("churnCount", churn);
                point.put("riskLevel", churn > maxChurn * 0.5 ? "HIGH" : churn > maxChurn * 0.2 ? "MEDIUM" : "LOW");
                riskPoints.add(point);
            }
        }
        result.put("riskPoints", riskPoints);
        
        return result;
    }

    private long countNewUsers(LocalDate startDate, LocalDate endDate) {
        LocalDateTime start = startDate.atStartOfDay();
        LocalDateTime end = endDate.atTime(23, 59, 59);
        
        return userRepository.findAll().stream()
                .filter(u -> u.getCreateTime() != null 
                        && !u.getCreateTime().isBefore(start) 
                        && !u.getCreateTime().isAfter(end))
                .count();
    }

    private long countLostUsers(String periodType, LocalDate startDate, LocalDate endDate) {
        LocalDate sevenDaysAgo = endDate.minusDays(7);
        
        List<Long> activeUsersBefore = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(0L, periodType, 
                        startDate, sevenDaysAgo)
                .stream()
                .map(CheckinRecord::getUserId)
                .distinct()
                .collect(Collectors.toList());
        
        List<Long> activeUsersAfter = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(0L, periodType, 
                        sevenDaysAgo, endDate)
                .stream()
                .map(CheckinRecord::getUserId)
                .distinct()
                .collect(Collectors.toList());
        
        return activeUsersBefore.stream()
                .filter(userId -> !activeUsersAfter.contains(userId))
                .count();
    }

    private long countRechecks(LocalDate startDate, LocalDate endDate) {
        List<CheckinRecord> records = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(0L, "DAILY", startDate, endDate);
        
        return records.stream()
                .filter(CheckinRecord::getIsRechecked)
                .count();
    }

    private int calculateMaxContinuousForUser(List<CheckinRecord> records) {
        if (records.isEmpty()) return 0;
        
        List<LocalDate> dates = records.stream()
                .map(CheckinRecord::getCheckinDate)
                .sorted()
                .collect(Collectors.toList());
        
        int maxStreak = 1;
        int currentStreak = 1;
        
        for (int i = 1; i < dates.size(); i++) {
            if (DateUtils.daysBetweenUtc(dates.get(i-1), dates.get(i)) == 1) {
                currentStreak++;
                maxStreak = Math.max(maxStreak, currentStreak);
            } else if (DateUtils.daysBetweenUtc(dates.get(i-1), dates.get(i)) > 1) {
                currentStreak = 1;
            }
        }
        
        return maxStreak;
    }

    private double calculateAvgPerWeek(List<CheckinRecord> records, LocalDate startDate, LocalDate endDate) {
        long totalDays = DateUtils.daysBetweenUtc(startDate, endDate) + 1;
        double weeks = totalDays / 7.0;
        return records.size() / weeks;
    }

    private Map<Integer, Long> analyzeWeekdayDistribution(List<CheckinRecord> records) {
        Map<Integer, Long> distribution = new TreeMap<>();
        
        for (CheckinRecord record : records) {
            int weekday = record.getCheckinDate().getDayOfWeek().getValue();
            distribution.merge(weekday, 1L, Long::sum);
        }
        
        return distribution;
    }

    private Map<String, Object> analyzeUserStreaks(Long userId, String periodType, List<CheckinRecord> records) {
        Map<String, Object> result = new HashMap<>();
        
        LocalDate today = DateUtils.getUtcToday();
        String period = DateUtils.getPeriodUtc(periodType, today);
        CheckinStats stats = statsRepository
                .findByUserIdAndPeriodTypeAndPeriod(userId, periodType, period)
                .orElse(null);
        
        result.put("currentStreak", stats != null ? stats.getContinuousDays() : 0);
        
        List<Integer> brokenStreaks = new ArrayList<>();
        List<LocalDate> dates = records.stream()
                .map(CheckinRecord::getCheckinDate)
                .sorted()
                .collect(Collectors.toList());
        
        int currentStreak = 1;
        for (int i = 1; i < dates.size(); i++) {
            if (DateUtils.daysBetweenUtc(dates.get(i-1), dates.get(i)) == 1) {
                currentStreak++;
            } else if (DateUtils.daysBetweenUtc(dates.get(i-1), dates.get(i)) > 1) {
                if (currentStreak > 1) {
                    brokenStreaks.add(currentStreak);
                }
                currentStreak = 1;
            }
        }
        
        result.put("brokenStreaks", brokenStreaks);
        result.put("avgBrokenStreakLength", 
                brokenStreaks.isEmpty() ? 0 : 
                Math.round(brokenStreaks.stream().mapToInt(Integer::intValue).average().orElse(0) * 10) / 10.0);
        
        return result;
    }

    private double calculateUserCheckinRate(Long userId, String periodType, LocalDate startDate, LocalDate endDate) {
        long totalDays = DateUtils.daysBetweenUtc(startDate, endDate) + 1;
        long checkinDays = checkinRecordRepository.countCheckinDays(
                userId, periodType, startDate, endDate);
        
        return totalDays > 0 ? Math.round(checkinDays * 10000.0 / totalDays) / 100.0 : 0;
    }

    private List<Map<String, Object>> generateTrendData(List<CheckinAnalysis> analyses) {
        return analyses.stream()
                .map(a -> {
                    Map<String, Object> point = new HashMap<>();
                    point.put("date", a.getAnalysisDate());
                    point.put("checkinRate", a.getCheckinRate());
                    point.put("checkedInUsers", a.getCheckedInUsers());
                    point.put("avgContinuousDays", a.getAvgContinuousDays());
                    point.put("churnRate", a.getChurnRate());
                    point.put("newUsers", a.getNewUsers());
                    point.put("lostUsers", a.getLostUsers());
                    return point;
                })
                .collect(Collectors.toList());
    }

    public Map<String, Object> getDashboardStats() {
        Map<String, Object> result = new HashMap<>();
        LocalDate today = DateUtils.getUtcToday();
        
        long totalUsers = userRepository.count();
        result.put("totalUsers", totalUsers);
        
        LocalDate monthStart = today.with(TemporalAdjusters.firstDayOfMonth());
        long monthCheckins = checkinRecordRepository.countCheckinDays(
                0L, "DAILY", monthStart, today);
        result.put("monthTotalCheckins", monthCheckins);
        
        long todayCheckins = checkinRecordRepository.countCheckinDays(
                0L, "DAILY", today, today);
        result.put("todayCheckins", todayCheckins);
        
        double todayCheckinRate = totalUsers > 0 ? (todayCheckins * 100.0 / totalUsers) : 0;
        result.put("todayCheckinRate", Math.round(todayCheckinRate * 100) / 100.0);
        
        Map<String, Object> recentChurn = analyzeChurnPoints(
                "DAILY", today.minusMonths(1), today);
        result.put("topChurnDay", recentChurn.get("churnDay"));
        result.put("topChurnRate", recentChurn.get("churnRate"));
        
        List<CheckinAnalysis> latestAnalyses = analysisRepository
                .findLatestAnalysis("DAILY", 7);
        result.put("weekTrend", generateTrendData(latestAnalyses));
        
        return result;
    }
}
