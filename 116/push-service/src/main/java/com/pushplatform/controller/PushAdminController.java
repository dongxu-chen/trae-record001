package com.pushplatform.controller;

import com.pushplatform.common.core.Result;
import com.pushplatform.push.ApnsCertificateManager;
import com.pushplatform.service.CallbackIdempotentService;
import com.pushplatform.service.TokenManageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/admin")
public class PushAdminController {

    private static final Logger logger = LoggerFactory.getLogger(PushAdminController.class);

    @Autowired
    private ApnsCertificateManager apnsCertificateManager;

    @Autowired
    private TokenManageService tokenManageService;

    @Autowired
    private CallbackIdempotentService callbackIdempotentService;

    @GetMapping("/apns/cert/status")
    public Result<Map<String, Object>> getApnsCertStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("valid", apnsCertificateManager.isCertificateValid());
        status.put("expiryDate", apnsCertificateManager.getCertificateExpiryDate());
        status.put("daysUntilExpiry", apnsCertificateManager.getDaysUntilExpiry());
        return Result.success(status);
    }

    @PostMapping("/apns/cert/reload")
    public Result<Boolean> reloadApnsCert() {
        logger.info("Reloading APNS certificate...");
        boolean success = apnsCertificateManager.reloadCertificate();
        return Result.success(success);
    }

    @GetMapping("/token/clean/count")
    public Result<Long> getInvalidTokenCount() {
        return Result.success(tokenManageService.getInvalidTokenCount());
    }

    @GetMapping("/callback/cache/count")
    public Result<Long> getCallbackCacheCount() {
        return Result.success(callbackIdempotentService.getProcessedCount());
    }

    @PostMapping("/callback/cache/clear")
    public Result<Boolean> clearCallbackCache() {
        logger.info("Clearing callback cache...");
        callbackIdempotentService.clearAll();
        return Result.success(true);
    }

    @GetMapping("/stats")
    public Result<Map<String, Object>> getStats() {
        Map<String, Object> stats = new HashMap<>();
        
        Map<String, Object> apnsCert = new HashMap<>();
        apnsCert.put("valid", apnsCertificateManager.isCertificateValid());
        apnsCert.put("expiryDate", apnsCertificateManager.getCertificateExpiryDate());
        apnsCert.put("daysUntilExpiry", apnsCertificateManager.getDaysUntilExpiry());
        stats.put("apnsCert", apnsCert);
        
        stats.put("invalidTokenCount", tokenManageService.getInvalidTokenCount());
        stats.put("callbackCacheCount", callbackIdempotentService.getProcessedCount());
        
        return Result.success(stats);
    }
}
