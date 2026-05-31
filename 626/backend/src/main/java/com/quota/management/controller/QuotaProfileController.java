package com.quota.management.controller;

import com.quota.management.common.Result;
import com.quota.management.entity.QuotaProfile;
import com.quota.management.entity.QuotaUsageHistory;
import com.quota.management.service.QuotaProfileService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/profile")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class QuotaProfileController {

    private final QuotaProfileService quotaProfileService;

    @GetMapping("/{tenantId}")
    public Result<QuotaProfile> getProfile(@PathVariable String tenantId,
                                            @RequestParam(defaultValue = "false") boolean refresh) {
        try {
            QuotaProfile profile = refresh ?
                    quotaProfileService.generateProfile(tenantId) :
                    quotaProfileService.getCachedProfile(tenantId);
            return Result.success(profile);
        } catch (RuntimeException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @GetMapping("/{tenantId}/generate")
    public Result<QuotaProfile> generateProfile(@PathVariable String tenantId) {
        try {
            QuotaProfile profile = quotaProfileService.generateProfile(tenantId);
            return Result.success(profile);
        } catch (RuntimeException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @GetMapping("/{tenantId}/history/{granularity}")
    public Result<List<QuotaUsageHistory>> getHistory(@PathVariable String tenantId,
                                                       @PathVariable String granularity,
                                                       @RequestParam(defaultValue = "100") int limit) {
        List<QuotaUsageHistory> history = quotaProfileService.getHistory(tenantId, granularity, limit);
        return Result.success(history);
    }
}
