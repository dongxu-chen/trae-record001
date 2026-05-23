package com.pushcenter.controller;

import com.pushcenter.dto.PushRequest;
import com.pushcenter.dto.PushResponse;
import com.pushcenter.enums.MessagePriority;
import com.pushcenter.enums.PushChannel;
import com.pushcenter.service.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/push")
public class PushController {

    @Resource
    private PushService pushService;

    @Resource
    private TemplateService templateService;

    @Resource
    private MessageStatisticsService statisticsService;

    @Resource
    private RetryService retryService;

    @Resource
    private RateLimitService rateLimitService;

    @Resource
    private ChannelHealthService channelHealthService;

    @Resource
    private PushAnalyticsService analyticsService;

    @PostMapping("/send")
    public PushResponse send(@Validated @RequestBody PushRequest request) {
        try {
            PushChannel preferredChannel = null;
            if (request.getPreferredChannel() != null) {
                preferredChannel = PushChannel.fromCode(request.getPreferredChannel());
            }

            MessagePriority priority = null;
            if (request.getPriority() != null) {
                priority = MessagePriority.fromCode(request.getPriority());
            }

            String messageId = pushService.push(
                    request.getUserId(),
                    request.getTemplateCode(),
                    request.getVariables(),
                    preferredChannel,
                    priority,
                    Boolean.TRUE.equals(request.getJumpQueue())
            );

            if (messageId != null) {
                return PushResponse.builder()
                        .success(true)
                        .messageId(messageId)
                        .message("Message queued successfully")
                        .build();
            } else {
                return PushResponse.builder()
                        .success(false)
                        .message("Failed to queue message")
                        .build();
            }
        } catch (Exception e) {
            log.error("Error processing push request", e);
            return PushResponse.builder()
                    .success(false)
                    .message("Error: " + e.getMessage())
                    .build();
        }
    }

    @PostMapping("/direct")
    public PushResponse sendDirect(
            @RequestParam String userId,
            @RequestParam String channel,
            @RequestParam String title,
            @RequestParam String content,
            @RequestParam(required = false) String priority,
            @RequestParam(required = false, defaultValue = "false") boolean jumpQueue) {
        try {
            PushChannel pushChannel = PushChannel.fromCode(channel);
            if (pushChannel == null) {
                return PushResponse.builder()
                        .success(false)
                        .message("Invalid channel: " + channel)
                        .build();
            }

            MessagePriority msgPriority = priority != null ? MessagePriority.fromCode(priority) : null;

            String messageId = pushService.pushDirect(userId, pushChannel, title, content, msgPriority, jumpQueue);

            if (messageId != null) {
                return PushResponse.builder()
                        .success(true)
                        .messageId(messageId)
                        .channel(channel)
                        .message("Message queued successfully")
                        .build();
            } else {
                return PushResponse.builder()
                        .success(false)
                        .message("Failed to queue message")
                        .build();
            }
        } catch (Exception e) {
            log.error("Error processing direct push request", e);
            return PushResponse.builder()
                    .success(false)
                    .message("Error: " + e.getMessage())
                    .build();
        }
    }

    @GetMapping("/templates")
    public Map<String, Object> getTemplates() {
        Map<String, Object> result = new HashMap<>();
        result.put("templates", templateService.getAllTemplates());
        return result;
    }

    @GetMapping("/statistics")
    public Map<String, Object> getStatistics() {
        return statisticsService.getAllStats();
    }

    @GetMapping("/queue/pending")
    public Map<String, Object> getPendingCounts() {
        Map<String, Object> result = new HashMap<>();
        Map<MessagePriority, Long> counts = pushService.getPendingCounts();
        for (Map.Entry<MessagePriority, Long> entry : counts.entrySet()) {
            result.put(entry.getKey().getCode(), entry.getValue());
        }
        return result;
    }

    @GetMapping("/retry/count")
    public Map<String, Object> getRetryCount() {
        Map<String, Object> result = new HashMap<>();
        result.put("pendingRetryCount", retryService.getPendingRetryCount());
        return result;
    }

    @GetMapping("/retry/statistics")
    public Map<String, Object> getRetryStatistics() {
        return retryService.getRetryStatistics();
    }

    @GetMapping("/retry/list")
    public Map<String, Object> getPendingRetries(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        Map<String, Object> result = new HashMap<>();
        result.put("list", retryService.getPendingRetries(page, size));
        result.put("total", retryService.getPendingRetryCount());
        result.put("page", page);
        result.put("size", size);
        return result;
    }

    @GetMapping("/retry/{messageId}")
    public Map<String, Object> getRetryDetail(@PathVariable String messageId) {
        Map<String, Object> result = new HashMap<>();
        result.put("state", retryService.getRetryState(messageId));
        result.put("history", retryService.getRetryHistory(messageId));
        return result;
    }

    @DeleteMapping("/retry/{messageId}")
    public Map<String, Object> cancelRetry(@PathVariable String messageId) {
        Map<String, Object> result = new HashMap<>();
        retryService.deleteRetryState(messageId);
        result.put("success", true);
        result.put("message", "Retry cancelled successfully");
        return result;
    }

    @GetMapping("/rate-limit")
    public Map<String, Object> getRateLimitInfo() {
        return rateLimitService.getAllRateLimitInfo();
    }

    @GetMapping("/rate-limit/{channel}")
    public Map<String, Object> getChannelRateLimitInfo(@PathVariable String channel) {
        PushChannel pushChannel = PushChannel.fromCode(channel);
        if (pushChannel == null) {
            Map<String, Object> result = new HashMap<>();
            result.put("error", "Invalid channel: " + channel);
            return result;
        }
        return rateLimitService.getChannelRateLimitInfo(pushChannel);
    }

    @PostMapping("/rate-limit/{channel}/reset")
    public Map<String, Object> resetRateLimit(@PathVariable String channel) {
        Map<String, Object> result = new HashMap<>();
        PushChannel pushChannel = PushChannel.fromCode(channel);
        if (pushChannel == null) {
            result.put("success", false);
            result.put("message", "Invalid channel: " + channel);
            return result;
        }
        rateLimitService.resetLimit(pushChannel);
        result.put("success", true);
        result.put("message", "Rate limit reset successfully for " + channel);
        return result;
    }

    @PostMapping("/rate-limit/{channel}/update")
    public Map<String, Object> updateRateLimit(
            @PathVariable String channel,
            @RequestParam long rate,
            @RequestParam long capacity) {
        Map<String, Object> result = new HashMap<>();
        PushChannel pushChannel = PushChannel.fromCode(channel);
        if (pushChannel == null) {
            result.put("success", false);
            result.put("message", "Invalid channel: " + channel);
            return result;
        }
        rateLimitService.updateRateLimit(pushChannel, rate, capacity);
        result.put("success", true);
        result.put("message", "Rate limit updated successfully");
        return result;
    }

    @GetMapping("/health")
    public Map<String, Object> getChannelHealth() {
        return channelHealthService.getAllHealthInfo();
    }

    @GetMapping("/health/{channel}")
    public Map<String, Object> getChannelHealthDetail(@PathVariable String channel) {
        PushChannel pushChannel = PushChannel.fromCode(channel);
        if (pushChannel == null) {
            Map<String, Object> result = new HashMap<>();
            result.put("error", "Invalid channel: " + channel);
            return result;
        }
        return channelHealthService.getChannelHealthInfo(pushChannel);
    }

    @PostMapping("/health/{channel}/recover")
    public Map<String, Object> forceRecoverChannel(@PathVariable String channel) {
        Map<String, Object> result = new HashMap<>();
        PushChannel pushChannel = PushChannel.fromCode(channel);
        if (pushChannel == null) {
            result.put("success", false);
            result.put("message", "Invalid channel: " + channel);
            return result;
        }
        channelHealthService.forceRecover(pushChannel);
        result.put("success", true);
        result.put("message", "Channel " + channel + " forcefully recovered");
        return result;
    }

    @PostMapping("/health/{channel}/degrade")
    public Map<String, Object> forceDegradeChannel(@PathVariable String channel) {
        Map<String, Object> result = new HashMap<>();
        PushChannel pushChannel = PushChannel.fromCode(channel);
        if (pushChannel == null) {
            result.put("success", false);
            result.put("message", "Invalid channel: " + channel);
            return result;
        }
        channelHealthService.forceDegrade(pushChannel);
        result.put("success", true);
        result.put("message", "Channel " + channel + " forcefully degraded");
        return result;
    }

    @GetMapping("/analytics")
    public Map<String, Object> getAnalytics(
            @RequestParam(defaultValue = "7") int days) {
        return analyticsService.getAllChannelAnalytics(days);
    }

    @GetMapping("/analytics/{channel}")
    public Map<String, Object> getChannelAnalytics(
            @PathVariable String channel,
            @RequestParam(defaultValue = "7") int days) {
        PushChannel pushChannel = PushChannel.fromCode(channel);
        if (pushChannel == null) {
            Map<String, Object> result = new HashMap<>();
            result.put("error", "Invalid channel: " + channel);
            return result;
        }
        return analyticsService.getChannelAnalytics(pushChannel, days);
    }

    @PostMapping("/analytics/arrival/{messageId}")
    public Map<String, Object> recordArrival(@PathVariable String messageId) {
        Map<String, Object> result = new HashMap<>();
        Map<String, Object> metadata = analyticsService.getMessageMetadata(messageId);
        if (metadata != null && metadata.get("channel") != null) {
            PushChannel channel = PushChannel.fromCode((String) metadata.get("channel"));
            if (channel != null) {
                analyticsService.recordArrival(channel, messageId);
            }
        }
        result.put("success", true);
        result.put("message", "Arrival recorded");
        return result;
    }

    @PostMapping("/analytics/click/{messageId}")
    public Map<String, Object> recordClick(@PathVariable String messageId) {
        Map<String, Object> result = new HashMap<>();
        analyticsService.recordClick(messageId);
        result.put("success", true);
        result.put("message", "Click recorded");
        return result;
    }

    @PostMapping("/analytics/conversion/{messageId}")
    public Map<String, Object> recordConversion(
            @PathVariable String messageId,
            @RequestParam(defaultValue = "default") String type) {
        Map<String, Object> result = new HashMap<>();
        analyticsService.recordConversion(messageId, type);
        result.put("success", true);
        result.put("message", "Conversion recorded");
        return result;
    }

    @GetMapping("/analytics/message/{messageId}")
    public Map<String, Object> getMessageAnalytics(@PathVariable String messageId) {
        Map<String, Object> result = new HashMap<>();
        result.put("metadata", analyticsService.getMessageMetadata(messageId));
        result.put("timeline", analyticsService.getEventTimeline(messageId));
        return result;
    }

    @PostMapping("/ab-test/create")
    public Map<String, Object> createABTest(
            @RequestParam String testName,
            @RequestParam List<String> variantNames,
            @RequestParam List<String> templateCodes) {
        Map<String, Object> result = new HashMap<>();
        if (variantNames.size() != templateCodes.size()) {
            result.put("success", false);
            result.put("message", "variantNames and templateCodes must have the same size");
            return result;
        }
        String testId = analyticsService.createABTest(testName, variantNames, templateCodes);
        result.put("success", true);
        result.put("testId", testId);
        result.put("message", "A/B Test created successfully");
        return result;
    }

    @PostMapping("/ab-test/{testId}/assign/{userId}")
    public Map<String, Object> assignABTestVariant(
            @PathVariable String testId,
            @PathVariable String userId) {
        Map<String, Object> result = new HashMap<>();
        String variant = analyticsService.assignABTestVariant(testId, userId);
        result.put("userId", userId);
        result.put("variant", variant);
        result.put("success", variant != null);
        return result;
    }

    @GetMapping("/ab-test/{testId}/results")
    public Map<String, Object> getABTestResults(@PathVariable String testId) {
        return analyticsService.getABTestResults(testId);
    }

    @PostMapping("/ab-test/{testId}/stop")
    public Map<String, Object> stopABTest(
            @PathVariable String testId,
            @RequestParam(required = false) String winner) {
        Map<String, Object> result = new HashMap<>();
        analyticsService.stopABTest(testId, winner);
        result.put("success", true);
        result.put("message", "A/B Test stopped successfully");
        return result;
    }
}
