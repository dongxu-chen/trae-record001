package com.checkin.service;

import com.checkin.dto.CheckinCalendarVO;
import com.checkin.entity.*;
import com.checkin.repository.*;
import com.checkin.util.DateUtils;
import com.checkin.util.SafeSandbox;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAdjusters;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class CheckinService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private CheckinRecordRepository checkinRecordRepository;

    @Autowired
    private CheckinConfigRepository checkinConfigRepository;

    @Autowired
    private CheckinTreasureRepository checkinTreasureRepository;

    @Autowired
    private UserTreasureRepository userTreasureRepository;

    @Autowired
    private CheckinStatsRepository checkinStatsRepository;

    private static final String CHECKIN_KEY_PREFIX = "checkin:";
    private static final String STATS_KEY_PREFIX = "checkin:stats:";
    private static final int MAX_RECHECK_DAYS = 7;
    private static final int MAX_RECHECK_PER_MONTH = 5;

    @Transactional
    public Map<String, Object> doCheckin(Long userId, String periodType) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        LocalDate todayUtc = DateUtils.getUtcToday();
        
        if (isCheckedIn(userId, todayUtc, periodType)) {
            throw new RuntimeException("今日已签到");
        }

        String period = DateUtils.getPeriodUtc(periodType, todayUtc);
        LocalDate startDate = DateUtils.getPeriodStartUtc(periodType, todayUtc);

        CheckinRecord record = new CheckinRecord();
        record.setUserId(userId);
        record.setCheckinDate(todayUtc);
        record.setPeriodType(periodType);
        record.setIsRechecked(false);

        CheckinStats stats = getOrCreateStats(userId, periodType, period);
        
        LocalDate lastCheckinDate = findLastCheckinDate(userId, periodType, todayUtc);
        int newContinuousDays = DateUtils.calculateContinuousDaysUtc(
                lastCheckinDate, stats.getContinuousDays(), todayUtc);
        
        stats.setContinuousDays(newContinuousDays);
        stats.setTotalDays(stats.getTotalDays() + 1);

        int dayIndex = DateUtils.calculateDayIndexUtc(periodType, todayUtc, startDate);
        
        CheckinConfig config = checkinConfigRepository
                .findByPeriodTypeAndDayIndexAndEnabledTrue(periodType, dayIndex)
                .orElse(null);

        Map<String, Object> rewardInfo = new HashMap<>();
        int actualRewardValue = 0;
        
        if (config != null) {
            if (!checkCondition(config.getConditionExpression(), stats)) {
                throw new RuntimeException("不满足签到条件");
            }
            
            actualRewardValue = calculateActualReward(config, stats);
            
            rewardInfo.put("type", config.getRewardType());
            rewardInfo.put("value", actualRewardValue);
            rewardInfo.put("name", config.getRewardName());
            record.setReward(config.getRewardName() + "(" + actualRewardValue + ")");
            
            applyReward(user, config.getRewardType(), actualRewardValue);
        }

        checkinRecordRepository.save(record);
        checkinStatsRepository.save(stats);
        updateRedisCache(userId, periodType, period, todayUtc, stats);
        checkTreasureMilestone(userId, periodType, period, stats.getTotalDays());

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("date", todayUtc);
        result.put("continuousDays", stats.getContinuousDays());
        result.put("totalDays", stats.getTotalDays());
        result.put("reward", rewardInfo);
        result.put("points", user.getPoints());

        return result;
    }

    public CheckinCalendarVO getCalendar(Long userId, String periodType, LocalDate date) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        LocalDate todayUtc = DateUtils.getUtcToday();
        if (date == null) {
            date = todayUtc;
        }

        String period = DateUtils.getPeriodUtc(periodType, date);
        LocalDate startDate = DateUtils.getPeriodStartUtc(periodType, date);
        LocalDate endDate = DateUtils.getPeriodEndUtc(periodType, date);

        List<CheckinRecord> records = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(userId, periodType, startDate, endDate);

        List<LocalDate> checkinDates = records.stream()
                .filter(r -> !r.getIsRechecked())
                .map(CheckinRecord::getCheckinDate)
                .sorted()
                .collect(Collectors.toList());

        List<LocalDate> recheckDates = records.stream()
                .filter(CheckinRecord::getIsRechecked)
                .map(CheckinRecord::getCheckinDate)
                .sorted()
                .collect(Collectors.toList());

        CheckinStats stats = getOrCreateStats(userId, periodType, period);

        int dayIndex = DateUtils.calculateDayIndexUtc(periodType, todayUtc, startDate);
        List<CheckinConfig> configs = checkinConfigRepository
                .findByPeriodTypeAndEnabledTrueOrderByDayIndexAsc(periodType);

        Map<String, Object> todayReward = new HashMap<>();
        Optional<CheckinConfig> todayConfig = configs.stream()
                .filter(c -> c.getDayIndex().equals(dayIndex + 1))
                .findFirst();
        if (todayConfig.isPresent()) {
            CheckinConfig cfg = todayConfig.get();
            todayReward.put("dayIndex", cfg.getDayIndex());
            todayReward.put("type", cfg.getRewardType());
            todayReward.put("value", calculateActualReward(cfg, stats));
            todayReward.put("name", cfg.getRewardName());
        }

        List<Map<String, Object>> rewardList = configs.stream()
                .map(cfg -> {
                    Map<String, Object> map = new HashMap<>();
                    map.put("dayIndex", cfg.getDayIndex());
                    map.put("type", cfg.getRewardType());
                    map.put("value", calculateActualReward(cfg, stats));
                    map.put("name", cfg.getRewardName());
                    map.put("achieved", cfg.getDayIndex() <= stats.getContinuousDays());
                    return map;
                })
                .collect(Collectors.toList());

        List<CheckinTreasure> treasures = checkinTreasureRepository
                .findByPeriodTypeAndEnabledTrueOrderByTotalDaysAsc(periodType);
        List<UserTreasure> userTreasures = userTreasureRepository
                .findByUserIdAndPeriod(userId, period);
        Map<Long, UserTreasure> userTreasureMap = userTreasures.stream()
                .collect(Collectors.toMap(UserTreasure::getTreasureId, ut -> ut));

        List<Map<String, Object>> treasureList = treasures.stream()
                .map(t -> {
                    Map<String, Object> map = new HashMap<>();
                    map.put("id", t.getId());
                    map.put("totalDays", t.getTotalDays());
                    map.put("type", t.getRewardType());
                    map.put("value", calculateActualTreasureReward(t, stats));
                    map.put("name", t.getRewardName());
                    map.put("icon", t.getIcon());
                    map.put("achieved", stats.getTotalDays() >= t.getTotalDays());
                    
                    UserTreasure ut = userTreasureMap.get(t.getId());
                    map.put("claimed", ut != null && ut.getClaimed());
                    return map;
                })
                .collect(Collectors.toList());

        YearMonth currentMonth = YearMonth.from(todayUtc);
        List<CheckinRecord> monthRecords = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(
                        userId, periodType, 
                        currentMonth.atDay(1), currentMonth.atEndOfMonth());
        int recheckCountThisMonth = (int) monthRecords.stream()
                .filter(CheckinRecord::getIsRechecked)
                .count();
        
        int remainingRecheck = MAX_RECHECK_PER_MONTH - recheckCountThisMonth;

        CheckinCalendarVO vo = new CheckinCalendarVO();
        vo.setPeriodType(periodType);
        vo.setPeriod(period);
        vo.setContinuousDays(stats.getContinuousDays());
        vo.setTotalDays(stats.getTotalDays());
        vo.setCheckinDates(checkinDates);
        vo.setRecheckDates(recheckDates);
        vo.setTodayReward(todayReward);
        vo.setRewards(rewardList);
        vo.setTreasures(treasureList);
        vo.setRecheckCards(user.getRecheckCards());
        vo.setRemainingRecheckCount(Math.max(0, remainingRecheck));
        vo.setTodayChecked(isCheckedIn(userId, todayUtc, periodType));

        return vo;
    }

    @Transactional
    public Map<String, Object> recheck(Long userId, String periodType, LocalDate checkinDate) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        LocalDate todayUtc = DateUtils.getUtcToday();
        
        if (!DateUtils.isWithinRecheckWindow(checkinDate, MAX_RECHECK_DAYS)) {
            throw new RuntimeException("只能补签过去" + MAX_RECHECK_DAYS + "天内的日期");
        }

        if (isCheckedIn(userId, checkinDate, periodType)) {
            throw new RuntimeException("该日期已签到");
        }

        if (user.getRecheckCards() <= 0) {
            throw new RuntimeException("补签卡不足");
        }

        YearMonth currentMonth = YearMonth.from(todayUtc);
        List<CheckinRecord> monthRecords = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(
                        userId, periodType, 
                        currentMonth.atDay(1), currentMonth.atEndOfMonth());
        long recheckCount = monthRecords.stream()
                .filter(CheckinRecord::getIsRechecked)
                .count();
        
        if (recheckCount >= MAX_RECHECK_PER_MONTH) {
            throw new RuntimeException("本月补签次数已达上限");
        }

        String period = DateUtils.getPeriodUtc(periodType, checkinDate);

        CheckinRecord record = new CheckinRecord();
        record.setUserId(userId);
        record.setCheckinDate(checkinDate);
        record.setPeriodType(periodType);
        record.setIsRechecked(true);
        checkinRecordRepository.save(record);

        user.setRecheckCards(user.getRecheckCards() - 1);
        userRepository.save(user);

        CheckinStats stats = getOrCreateStats(userId, periodType, period);
        stats.setTotalDays(stats.getTotalDays() + 1);
        stats.setRecheckCount(stats.getRecheckCount() + 1);
        checkinStatsRepository.save(stats);

        checkTreasureMilestone(userId, periodType, period, stats.getTotalDays());

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("date", checkinDate);
        result.put("remainingCards", user.getRecheckCards());
        result.put("totalDays", stats.getTotalDays());
        result.put("maxRecheckDays", MAX_RECHECK_DAYS);

        return result;
    }

    @Transactional
    public Map<String, Object> claimTreasure(Long userId, Long treasureId) {
        CheckinTreasure treasure = checkinTreasureRepository.findById(treasureId)
                .orElseThrow(() -> new RuntimeException("宝箱不存在"));

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        LocalDate todayUtc = DateUtils.getUtcToday();
        String period = DateUtils.getPeriodUtc(treasure.getPeriodType(), todayUtc);
        LocalDate startDate = DateUtils.getPeriodStartUtc(treasure.getPeriodType(), todayUtc);
        LocalDate endDate = DateUtils.getPeriodEndUtc(treasure.getPeriodType(), todayUtc);

        int checkinCount = checkinRecordRepository.countCheckinDays(
                userId, treasure.getPeriodType(), startDate, endDate);
        
        if (checkinCount < treasure.getTotalDays()) {
            throw new RuntimeException("未达到领取条件");
        }

        UserTreasure userTreasure = userTreasureRepository
                .findByUserIdAndTreasureIdAndPeriod(userId, treasureId, period)
                .orElse(null);

        if (userTreasure != null && userTreasure.getClaimed()) {
            throw new RuntimeException("已领取过该奖励");
        }

        if (userTreasure == null) {
            userTreasure = new UserTreasure();
            userTreasure.setUserId(userId);
            userTreasure.setTreasureId(treasureId);
            userTreasure.setPeriod(period);
        }

        CheckinStats stats = getOrCreateStats(userId, treasure.getPeriodType(), period);
        int actualRewardValue = calculateActualTreasureReward(treasure, stats);
        
        if (!checkCondition(treasure.getConditionExpression(), stats)) {
            throw new RuntimeException("不满足领取条件");
        }

        userTreasure.setClaimed(true);
        userTreasure.setClaimTime(DateUtils.getUtcNow());
        userTreasureRepository.save(userTreasure);

        applyReward(user, treasure.getRewardType(), actualRewardValue);

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("name", treasure.getRewardName());
        result.put("type", treasure.getRewardType());
        result.put("value", actualRewardValue);

        return result;
    }

    public Map<String, Object> getStats(Long userId) {
        Map<String, Object> result = new HashMap<>();
        
        LocalDate todayUtc = DateUtils.getUtcToday();
        
        String[] periodTypes = {"DAILY", "WEEKLY", "MONTHLY"};
        Map<String, Object> periodStats = new HashMap<>();
        
        for (String periodType : periodTypes) {
            String period = DateUtils.getPeriodUtc(periodType, todayUtc);
            CheckinStats stats = checkinStatsRepository
                    .findByUserIdAndPeriodTypeAndPeriod(userId, periodType, period)
                    .orElse(null);
            
            Map<String, Object> statMap = new HashMap<>();
            if (stats != null) {
                statMap.put("continuousDays", stats.getContinuousDays());
                statMap.put("totalDays", stats.getTotalDays());
                statMap.put("recheckCount", stats.getRecheckCount());
            } else {
                statMap.put("continuousDays", 0);
                statMap.put("totalDays", 0);
                statMap.put("recheckCount", 0);
            }
            statMap.put("todayChecked", isCheckedIn(userId, todayUtc, periodType));
            periodStats.put(periodType.toLowerCase(), statMap);
        }
        
        result.put("periodStats", periodStats);
        result.put("maxRecheckDays", MAX_RECHECK_DAYS);
        result.put("maxRecheckPerMonth", MAX_RECHECK_PER_MONTH);
        
        User user = userRepository.findById(userId).orElse(null);
        if (user != null) {
            result.put("points", user.getPoints());
            result.put("recheckCards", user.getRecheckCards());
        }
        
        return result;
    }

    private LocalDate findLastCheckinDate(Long userId, String periodType, LocalDate today) {
        LocalDate startDate = today.minusMonths(1);
        List<CheckinRecord> records = checkinRecordRepository
                .findByUserIdAndPeriodTypeAndCheckinDateBetween(
                        userId, periodType, startDate, today.minusDays(1));
        
        return records.stream()
                .map(CheckinRecord::getCheckinDate)
                .max(LocalDate::compareTo)
                .orElse(null);
    }

    private boolean isCheckedIn(Long userId, LocalDate date, String periodType) {
        String key = CHECKIN_KEY_PREFIX + periodType + ":" + userId + ":" + date;
        Boolean cached = redisTemplate.hasKey(key);
        if (cached != null && cached) {
            return true;
        }
        boolean exists = checkinRecordRepository
                .existsByUserIdAndCheckinDateAndPeriodType(userId, date, periodType);
        if (exists) {
            redisTemplate.opsForValue().set(key, true, 2, TimeUnit.DAYS);
        }
        return exists;
    }

    private boolean checkCondition(String conditionExpression, CheckinStats stats) {
        if (conditionExpression == null || conditionExpression.trim().isEmpty()) {
            return true;
        }
        
        Map<String, Object> vars = new HashMap<>();
        vars.put("continuousDays", stats.getContinuousDays());
        vars.put("totalDays", stats.getTotalDays());
        vars.put("recheckCount", stats.getRecheckCount());
        
        return SafeSandbox.validateCondition(conditionExpression, vars);
    }

    private int calculateActualReward(CheckinConfig config, CheckinStats stats) {
        if (config.getRewardExpression() != null && !config.getRewardExpression().trim().isEmpty()) {
            try {
                return SafeSandbox.calculateReward(
                        config.getRewardExpression(),
                        stats.getContinuousDays(),
                        stats.getTotalDays(),
                        0
                );
            } catch (Exception e) {
                throw new RuntimeException("奖励计算表达式执行失败: " + e.getMessage());
            }
        }
        return config.getRewardValue() != null ? config.getRewardValue() : 0;
    }

    private int calculateActualTreasureReward(CheckinTreasure treasure, CheckinStats stats) {
        if (treasure.getRewardExpression() != null && !treasure.getRewardExpression().trim().isEmpty()) {
            try {
                return SafeSandbox.calculateReward(
                        treasure.getRewardExpression(),
                        stats.getContinuousDays(),
                        stats.getTotalDays(),
                        0
                );
            } catch (Exception e) {
                throw new RuntimeException("宝箱奖励计算表达式执行失败: " + e.getMessage());
            }
        }
        return treasure.getRewardValue() != null ? treasure.getRewardValue() : 0;
    }

    private void applyReward(User user, String rewardType, int value) {
        if ("POINTS".equals(rewardType)) {
            user.setPoints(user.getPoints() + value);
        } else if ("RECHECK_CARD".equals(rewardType)) {
            user.setRecheckCards(user.getRecheckCards() + value);
        }
        userRepository.save(user);
    }

    private CheckinStats getOrCreateStats(Long userId, String periodType, String period) {
        return checkinStatsRepository
                .findByUserIdAndPeriodTypeAndPeriod(userId, periodType, period)
                .orElseGet(() -> {
                    CheckinStats newStats = new CheckinStats();
                    newStats.setUserId(userId);
                    newStats.setPeriodType(periodType);
                    newStats.setPeriod(period);
                    newStats.setContinuousDays(0);
                    newStats.setTotalDays(0);
                    newStats.setRecheckCount(0);
                    return newStats;
                });
    }

    private void updateRedisCache(Long userId, String periodType, String period, 
                                  LocalDate date, CheckinStats stats) {
        String checkinKey = CHECKIN_KEY_PREFIX + periodType + ":" + userId + ":" + date;
        redisTemplate.opsForValue().set(checkinKey, true, 2, TimeUnit.DAYS);

        String statsKey = STATS_KEY_PREFIX + periodType + ":" + userId + ":" + period;
        Map<String, Integer> statsMap = new HashMap<>();
        statsMap.put("continuousDays", stats.getContinuousDays());
        statsMap.put("totalDays", stats.getTotalDays());
        redisTemplate.opsForValue().set(statsKey, statsMap, 1, TimeUnit.DAYS);
    }

    private void checkTreasureMilestone(Long userId, String periodType, String period, int totalDays) {
        List<CheckinTreasure> treasures = checkinTreasureRepository
                .findByPeriodTypeAndEnabledTrueOrderByTotalDaysAsc(periodType);
        
        for (CheckinTreasure treasure : treasures) {
            if (totalDays >= treasure.getTotalDays()) {
                UserTreasure userTreasure = userTreasureRepository
                        .findByUserIdAndTreasureIdAndPeriod(userId, treasure.getId(), period)
                        .orElse(null);
                
                if (userTreasure == null) {
                    userTreasure = new UserTreasure();
                    userTreasure.setUserId(userId);
                    userTreasure.setTreasureId(treasure.getId());
                    userTreasure.setPeriod(period);
                    userTreasure.setClaimed(false);
                    userTreasureRepository.save(userTreasure);
                }
            }
        }
    }
}
