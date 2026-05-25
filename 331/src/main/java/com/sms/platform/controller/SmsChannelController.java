package com.sms.platform.controller;

import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsChannelConfig;
import com.sms.platform.service.ChannelManagerService;
import com.sms.platform.service.RateLimiterService;
import com.sms.platform.service.ReceiptService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/channel")
public class SmsChannelController {

    @Resource
    private ChannelManagerService channelManagerService;

    @Resource
    private RateLimiterService rateLimiterService;

    @Resource
    private ReceiptService receiptService;

    @GetMapping("/list")
    public Result<List<SmsChannelConfig>> listChannels() {
        return Result.success(channelManagerService.getAllChannelConfigs());
    }

    @GetMapping("/healthy")
    public Result<List<SmsChannelConfig>> listHealthyChannels() {
        return Result.success(channelManagerService.getHealthyChannels());
    }

    @GetMapping("/select")
    public Result<SmsChannelConfig> selectChannel() {
        return Result.success(channelManagerService.selectChannel());
    }

    @PostMapping("/refresh")
    public Result<Void> refreshCache() {
        channelManagerService.refreshChannelCache();
        return Result.success();
    }

    @GetMapping("/rate/{channelCode}")
    public Result<Map<String, Object>> getRateLimitStatus(@PathVariable Integer channelCode) {
        Map<String, Object> data = rateLimiterService.getTokenBucketStatus(channelCode);
        return Result.success(data);
    }

    @PostMapping("/rate/reset/{channelCode}")
    public Result<Void> resetRateLimit(@PathVariable Integer channelCode) {
        rateLimiterService.resetLimit(channelCode);
        return Result.success();
    }

    @PostMapping("/rate/refill/{channelCode}")
    public Result<Void> refillTokenBucket(@PathVariable Integer channelCode) {
        rateLimiterService.refillBucket(channelCode);
        return Result.success();
    }

    @PostMapping("/health/check")
    public Result<Void> triggerHealthCheck() {
        channelManagerService.healthCheckTask();
        return Result.success();
    }

    @PostMapping("/receipt/check")
    public Result<Void> triggerReceiptCheck() {
        receiptService.checkReceiptTimeout();
        return Result.success();
    }

    @GetMapping("/receipt/timeout/count/{channelCode}")
    public Result<Map<String, Object>> getReceiptTimeoutCount(@PathVariable Integer channelCode) {
        Map<String, Object> data = new HashMap<>();
        data.put("channelCode", channelCode);
        data.put("timeoutCount", receiptService.getReceiptTimeoutCount(channelCode));

        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config != null) {
            data.put("maxTimeoutCount", config.getMaxReceiptTimeoutCount());
            data.put("receiptTimeoutSeconds", config.getReceiptTimeoutSeconds());
        }

        return Result.success(data);
    }

    @PostMapping("/receipt/timeout/reset/{channelCode}")
    public Result<Void> resetReceiptTimeoutCount(@PathVariable Integer channelCode) {
        receiptService.resetReceiptTimeoutCount(channelCode);
        return Result.success();
    }

    @PostMapping("/receipt/update")
    public Result<Map<String, Boolean>> updateReceipt(
            @RequestParam(required = false) String externalSerialNo,
            @RequestParam(required = false) String serialNo,
            @RequestParam Integer receiptStatus,
            @RequestParam(required = false) String receiptContent) {
        boolean success;
        if (externalSerialNo != null && !externalSerialNo.isEmpty()) {
            success = receiptService.updateReceipt(externalSerialNo, receiptStatus, receiptContent);
        } else if (serialNo != null && !serialNo.isEmpty()) {
            success = receiptService.updateReceiptBySerialNo(serialNo, receiptStatus, receiptContent);
        } else {
            success = false;
        }

        Map<String, Boolean> data = new HashMap<>();
        data.put("success", success);
        return Result.success(data);
    }
}
