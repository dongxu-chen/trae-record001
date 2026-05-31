package com.checkin.controller;

import com.checkin.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.checkin.service.ShareService;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/share")
public class ShareController {

    @Autowired
    private ShareService shareService;

    @PostMapping("/create")
    public Result<Map<String, Object>> createShare(@RequestBody Map<String, Object> params) {
        try {
            Long userId = Long.valueOf(params.get("userId").toString());
            String periodType = (String) params.getOrDefault("periodType", "DAILY");
            String platform = (String) params.getOrDefault("platform", "APP");
            
            Map<String, Object> result = shareService.createShare(userId, periodType, platform);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/claim/{shareId}")
    public Result<Map<String, Object>> claimShareReward(@PathVariable Long shareId) {
        try {
            Map<String, Object> result = shareService.claimShareReward(shareId);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/history/{userId}")
    public Result<List<Map<String, Object>>> getShareHistory(@PathVariable Long userId) {
        try {
            List<Map<String, Object>> history = shareService.getShareHistory(userId);
            return Result.success(history);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/stats/{userId}")
    public Result<Map<String, Object>> getShareStats(@PathVariable Long userId) {
        try {
            Map<String, Object> stats = shareService.getShareStats(userId);
            return Result.success(stats);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/{shareId}/action")
    public Result<Map<String, Object>> incrementShareStats(
            @PathVariable Long shareId,
            @RequestParam String action) {
        try {
            Map<String, Object> result = shareService.incrementShareStats(shareId, action);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/platforms")
    public Result<List<Map<String, Object>>> getSharePlatforms() {
        List<Map<String, Object>> platforms = List.of(
            Map.of("platform", "WECHAT", "name", "微信", "icon", "💬"),
            Map.of("platform", "WEIBO", "name", "微博", "icon", "📢"),
            Map.of("platform", "QQ", "name", "QQ", "icon", "🐧"),
            Map.of("platform", "MOMENTS", "name", "朋友圈", "icon", "🖼️"),
            Map.of("platform", "APP", "name", "应用内", "icon", "📱")
        );
        return Result.success(platforms);
    }

    @GetMapping("/rewards")
    public Result<Map<String, Object>> getShareRewards() {
        Map<String, Object> rewards = Map.of(
            "dailyReward", 20,
            "weeklyBonus", 100,
            "weeklyBonusThreshold", 7,
            "description", "每日分享可获得20积分，每周累计分享7天额外获得100积分奖励"
        );
        return Result.success(rewards);
    }
}
