package com.checkin.service;

import com.checkin.entity.*;
import com.checkin.repository.*;
import com.checkin.util.DateUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
public class ShareService {

    @Autowired
    private CheckinShareRepository shareRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private CheckinRecordRepository checkinRecordRepository;

    @Autowired
    private CheckinStatsRepository statsRepository;

    private static final int DAILY_SHARE_REWARD_POINTS = 20;
    private static final int WEEKLY_SHARE_BONUS_POINTS = 100;
    private static final String SHARE_REWARD_TYPE = "POINTS";

    @Transactional
    public Map<String, Object> createShare(Long userId, String periodType, String platform) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        LocalDate today = DateUtils.getUtcToday();
        
        if (!checkinRecordRepository.existsByUserIdAndCheckinDateAndPeriodType(
                userId, today, periodType)) {
            throw new RuntimeException("请先完成今日签到后再分享");
        }

        Optional<CheckinShare> existingShare = shareRepository
                .findByUserIdAndShareDate(userId, today);
        
        if (existingShare.isPresent() && existingShare.get().getRewardClaimed()) {
            throw new RuntimeException("今日已分享并领取过奖励");
        }

        String period = DateUtils.getPeriodUtc(periodType, today);
        CheckinStats stats = statsRepository
                .findByUserIdAndPeriodTypeAndPeriod(userId, periodType, period)
                .orElse(null);
        
        int continuousDays = stats != null ? stats.getContinuousDays() : 0;
        int totalDays = stats != null ? stats.getTotalDays() : 0;

        String shareContent = generateShareContent(user.getNickname(), continuousDays, totalDays, today);
        String shareImage = generateShareImage(continuousDays, totalDays);

        CheckinShare share = existingShare.orElseGet(() -> {
            CheckinShare newShare = new CheckinShare();
            newShare.setUserId(userId);
            newShare.setShareDate(today);
            return newShare;
        });
        
        share.setSharePlatform(platform);
        share.setShareContent(shareContent);
        share.setShareImage(shareImage);
        share.setRewardType(SHARE_REWARD_TYPE);
        share.setRewardValue(DAILY_SHARE_REWARD_POINTS);
        
        shareRepository.save(share);

        Map<String, Object> result = new HashMap<>();
        result.put("shareId", share.getId());
        result.put("shareContent", shareContent);
        result.put("shareImage", shareImage);
        result.put("shareDate", today);
        result.put("rewardPoints", DAILY_SHARE_REWARD_POINTS);
        result.put("canClaimReward", !share.getRewardClaimed());
        
        return result;
    }

    @Transactional
    public Map<String, Object> claimShareReward(Long shareId) {
        CheckinShare share = shareRepository.findById(shareId)
                .orElseThrow(() -> new RuntimeException("分享记录不存在"));

        if (share.getRewardClaimed()) {
            throw new RuntimeException("该分享奖励已领取");
        }

        User user = userRepository.findById(share.getUserId())
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        int rewardValue = share.getRewardValue() != null ? share.getRewardValue() : DAILY_SHARE_REWARD_POINTS;
        int bonusPoints = 0;
        
        LocalDate weekStart = DateUtils.getPeriodStartUtc("WEEKLY", share.getShareDate());
        LocalDate weekEnd = DateUtils.getPeriodEndUtc("WEEKLY", share.getShareDate());
        List<CheckinShare> weekShares = shareRepository
                .findByUserIdAndShareDateBetween(share.getUserId(), weekStart, weekEnd);
        
        long claimedThisWeek = weekShares.stream()
                .filter(s -> s.getRewardClaimed() && !s.getId().equals(shareId))
                .count();
        
        if (claimedThisWeek >= 6) {
            bonusPoints = WEEKLY_SHARE_BONUS_POINTS;
        }

        int totalReward = rewardValue + bonusPoints;
        user.setPoints(user.getPoints() + totalReward);
        userRepository.save(user);

        share.setRewardClaimed(true);
        shareRepository.save(share);

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("rewardType", share.getRewardType());
        result.put("baseReward", rewardValue);
        result.put("bonusReward", bonusPoints);
        result.put("totalReward", totalReward);
        result.put("newPoints", user.getPoints());
        result.put("weeklyShareCount", claimedThisWeek + 1);
        
        return result;
    }

    public List<Map<String, Object>> getShareHistory(Long userId) {
        List<CheckinShare> shares = shareRepository.findByUserIdOrderByCreateTimeDesc(userId);
        
        return shares.stream().map(share -> {
            Map<String, Object> map = new HashMap<>();
            map.put("id", share.getId());
            map.put("shareDate", share.getShareDate());
            map.put("platform", share.getSharePlatform());
            map.put("viewCount", share.getViewCount());
            map.put("likeCount", share.getLikeCount());
            map.put("rewardClaimed", share.getRewardClaimed());
            map.put("rewardValue", share.getRewardValue());
            map.put("createTime", share.getCreateTime());
            return map;
        }).collect(java.util.stream.Collectors.toList());
    }

    @Transactional
    public Map<String, Object> incrementShareStats(Long shareId, String action) {
        CheckinShare share = shareRepository.findById(shareId)
                .orElseThrow(() -> new RuntimeException("分享记录不存在"));

        if ("view".equals(action)) {
            share.setViewCount(share.getViewCount() + 1);
        } else if ("like".equals(action)) {
            share.setLikeCount(share.getLikeCount() + 1);
        }
        
        shareRepository.save(share);

        Map<String, Object> result = new HashMap<>();
        result.put("viewCount", share.getViewCount());
        result.put("likeCount", share.getLikeCount());
        
        return result;
    }

    public Map<String, Object> getShareStats(Long userId) {
        Map<String, Object> result = new HashMap<>();
        
        List<CheckinShare> allShares = shareRepository.findByUserIdOrderByCreateTimeDesc(userId);
        result.put("totalShares", allShares.size());
        
        Integer claimedCount = shareRepository.countClaimedShares(userId);
        result.put("claimedRewards", claimedCount != null ? claimedCount : 0);
        
        Long totalViews = shareRepository.sumViewCount(userId);
        result.put("totalViews", totalViews != null ? totalViews : 0);
        
        int totalLikes = allShares.stream()
                .mapToInt(CheckinShare::getLikeCount)
                .sum();
        result.put("totalLikes", totalLikes);
        
        LocalDate today = DateUtils.getUtcToday();
        Optional<CheckinShare> todayShare = shareRepository.findByUserIdAndShareDate(userId, today);
        result.put("todayShared", todayShare.isPresent());
        result.put("todayRewardClaimed", todayShare.map(CheckinShare::getRewardClaimed).orElse(false));
        
        LocalDate weekStart = DateUtils.getPeriodStartUtc("WEEKLY", today);
        List<CheckinShare> weekShares = shareRepository
                .findByUserIdAndShareDateBetween(userId, weekStart, today);
        long weekClaimed = weekShares.stream()
                .filter(CheckinShare::getRewardClaimed)
                .count();
        result.put("weekClaimedCount", weekClaimed);
        result.put("nextWeeklyBonusAt", 7);
        result.put("canGetWeeklyBonus", weekClaimed >= 6);
        
        result.put("dailyReward", DAILY_SHARE_REWARD_POINTS);
        result.put("weeklyBonus", WEEKLY_SHARE_BONUS_POINTS);
        
        return result;
    }

    private String generateShareContent(String nickname, int continuousDays, int totalDays, LocalDate date) {
        String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy年MM月dd日"));
        
        List<String> templates = Arrays.asList(
            "%s在%s完成了签到！\n已连续签到%d天，累计签到%d天。\n坚持就是胜利，一起加油！💪",
            "签到打卡！%s今天又来啦~\n连续%d天不中断，累计%d天啦！\n你也来一起签到吧~",
            "每日签到，健康生活！\n%s于%s签到成功\n连续：%d天 | 累计：%d天\n邀你一起来挑战！🎯"
        );
        
        String template = templates.get(new Random().nextInt(templates.size()));
        return String.format(template, nickname, dateStr, continuousDays, totalDays);
    }

    private String generateShareImage(int continuousDays, int totalDays) {
        return String.format("https://checkin.example.com/share?c=%d&t=%d&r=%d",
                continuousDays, totalDays, System.currentTimeMillis());
    }
}
