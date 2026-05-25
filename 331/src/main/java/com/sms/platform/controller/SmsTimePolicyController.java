package com.sms.platform.controller;

import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsSendTimePolicy;
import com.sms.platform.service.SendTimePolicyService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/sms/time/policy")
public class SmsTimePolicyController {

    @Resource
    private SendTimePolicyService sendTimePolicyService;

    @PostMapping
    public Result<String> addPolicy(@RequestBody SmsSendTimePolicy policy) {
        sendTimePolicyService.addPolicy(policy);
        return Result.success("添加成功");
    }

    @PutMapping
    public Result<String> updatePolicy(@RequestBody SmsSendTimePolicy policy) {
        sendTimePolicyService.updatePolicy(policy);
        return Result.success("更新成功");
    }

    @DeleteMapping("/{id}")
    public Result<String> deletePolicy(@PathVariable Long id) {
        sendTimePolicyService.deletePolicy(id);
        return Result.success("删除成功");
    }

    @GetMapping("/{id}")
    public Result<SmsSendTimePolicy> getPolicy(@PathVariable Long id) {
        return Result.success(sendTimePolicyService.getPolicy(id));
    }

    @GetMapping("/list")
    public Result<List<SmsSendTimePolicy>> listPolicies() {
        return Result.success(sendTimePolicyService.listPolicies());
    }

    @PostMapping("/check")
    public Result<SendTimePolicyService.TimeCheckResult> checkSendAllowed(
            @RequestParam Integer smsType,
            @RequestParam(required = false) String sendTime) {
        if (sendTime != null && !sendTime.isEmpty()) {
            try {
                java.time.LocalDateTime time = java.time.LocalDateTime.parse(sendTime,
                        java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
                return Result.success(sendTimePolicyService.checkSendAllowed(smsType, time));
            } catch (Exception e) {
                return Result.error("时间格式不正确，请使用yyyy-MM-dd HH:mm:ss格式");
            }
        }
        return Result.success(sendTimePolicyService.checkSendAllowed(smsType));
    }

    @PostMapping("/refresh")
    public Result<String> refreshCache() {
        sendTimePolicyService.refreshCache();
        return Result.success("缓存刷新成功");
    }

    @GetMapping("/status")
    public Result<Map<String, Object>> getPolicyStatus() {
        return Result.success(sendTimePolicyService.getPolicyStatus());
    }
}
