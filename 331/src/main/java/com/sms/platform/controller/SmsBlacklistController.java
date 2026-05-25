package com.sms.platform.controller;

import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsBlacklist;
import com.sms.platform.service.BlacklistService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/blacklist")
public class SmsBlacklistController {

    @Resource
    private BlacklistService blacklistService;

    @PostMapping
    public Result<Void> addBlacklist(@RequestBody SmsBlacklist blacklist) {
        log.info("添加黑名单: mobile={}, smsType={}, isPrefixMatch={}",
                blacklist.getMobile(), blacklist.getSmsType(), blacklist.getIsPrefixMatch());
        blacklistService.addBlacklist(blacklist);
        return Result.success();
    }

    @PostMapping("/prefix")
    public Result<Void> addPrefixBlacklist(
            @RequestParam String prefix,
            @RequestParam(required = false) Integer smsType,
            @RequestParam(required = false) String reason) {
        log.info("添加前缀黑名单: prefix={}, smsType={}, reason={}", prefix, smsType, reason);
        blacklistService.addPrefixBlacklistBatch(prefix, smsType, reason);
        return Result.success();
    }

    @DeleteMapping
    public Result<Void> removeBlacklist(
            @RequestParam String mobile,
            @RequestParam(required = false) Integer smsType,
            @RequestParam(required = false) Integer isPrefixMatch) {
        log.info("移除黑名单: mobile={}, smsType={}, isPrefixMatch={}", mobile, smsType, isPrefixMatch);
        blacklistService.removeBlacklist(mobile, smsType, isPrefixMatch);
        return Result.success();
    }

    @DeleteMapping("/prefix")
    public Result<Void> removePrefixBlacklist(
            @RequestParam String prefix,
            @RequestParam(required = false) Integer smsType) {
        log.info("移除前缀黑名单: prefix={}, smsType={}", prefix, smsType);
        blacklistService.removePrefixBlacklist(prefix, smsType);
        return Result.success();
    }

    @PostMapping("/1069/block")
    public Result<Map<String, Object>> block1069Segment(
            @RequestParam(required = false) Integer smsType) {
        log.info("1069号段一键封禁: smsType={}", smsType);
        blacklistService.block1069Segment(smsType);

        Map<String, Object> result = new HashMap<>();
        result.put("blocked", true);
        result.put("prefixes", java.util.Arrays.asList("1069", "1068", "1065"));
        result.put("smsType", smsType);
        result.put("message", "1069等营销号段封禁成功");

        return Result.success(result);
    }

    @PostMapping("/1069/unblock")
    public Result<Map<String, Object>> unblock1069Segment(
            @RequestParam(required = false) Integer smsType) {
        log.info("解除1069号段封禁: smsType={}", smsType);
        blacklistService.unblock1069Segment(smsType);

        Map<String, Object> result = new HashMap<>();
        result.put("unblocked", true);
        result.put("prefixes", java.util.Arrays.asList("1069", "1068", "1065"));
        result.put("smsType", smsType);
        result.put("message", "1069等营销号段解封成功");

        return Result.success(result);
    }

    @GetMapping("/check")
    public Result<Map<String, Object>> checkBlacklist(
            @RequestParam String mobile,
            @RequestParam Integer smsType) {
        boolean blacklisted = blacklistService.isBlacklisted(mobile, smsType);
        Map<String, Object> data = new HashMap<>();
        data.put("blacklisted", blacklisted);
        data.put("mobile", mobile);
        data.put("smsType", smsType);
        return Result.success(data);
    }

    @GetMapping("/page")
    public Result<List<SmsBlacklist>> listBlacklist(
            @RequestParam(required = false) String mobile,
            @RequestParam(required = false) Integer smsType,
            @RequestParam(required = false) Integer isPrefixMatch) {
        return Result.success(blacklistService.listBlacklist(mobile, smsType, isPrefixMatch));
    }

    @GetMapping("/prefix/list")
    public Result<List<SmsBlacklist>> listAllPrefixBlacklist() {
        return Result.success(blacklistService.listAllPrefixBlacklist());
    }

    @GetMapping("/stats")
    public Result<Map<String, Object>> getBlacklistStats() {
        return Result.success(blacklistService.getBlacklistStats());
    }

    @PostMapping("/refresh")
    public Result<Void> refreshCache() {
        blacklistService.refreshCache();
        return Result.success();
    }
}
