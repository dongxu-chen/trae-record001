package com.pushplatform.controller;

import com.pushplatform.common.core.Result;
import com.pushplatform.entity.PushRecord;
import com.pushplatform.service.CallbackIdempotentService;
import com.pushplatform.service.PushRecordService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.List;
import java.util.concurrent.Executor;

@RestController
@RequestMapping("/api/record")
public class PushRecordController {

    private static final Logger logger = LoggerFactory.getLogger(PushRecordController.class);

    @Autowired
    private PushRecordService pushRecordService;

    @Autowired
    private CallbackIdempotentService callbackIdempotentService;

    @Resource(name = "callbackExecutor")
    private Executor callbackExecutor;

    @GetMapping("/task/{taskId}")
    public Result<List<PushRecord>> listByTaskId(@PathVariable Long taskId) {
        return Result.success(pushRecordService.listByTaskId(taskId));
    }

    @GetMapping("/taskNo/{taskNo}")
    public Result<List<PushRecord>> listByTaskNo(@PathVariable String taskNo) {
        return Result.success(pushRecordService.listByTaskNo(taskNo));
    }

    @GetMapping("/{id}")
    public Result<PushRecord> getById(@PathVariable Long id) {
        return Result.success(pushRecordService.getById(id));
    }

    @PostMapping("/callback/{id}")
    public Result<Boolean> callback(@PathVariable Long id,
                                    @RequestHeader(value = "X-Callback-Id", required = false) String callbackId,
                                    @RequestBody String callbackResult) {
        if (callbackId != null && !callbackId.isEmpty()) {
            if (callbackIdempotentService.isProcessed(callbackId)) {
                logger.info("Duplicate callback detected, id: {}, callbackId: {}", id, callbackId);
                return Result.success(true);
            }
            
            callbackIdempotentService.markProcessed(callbackId);
        }

        logger.info("Processing callback, id: {}, callbackId: {}", id, callbackId);
        
        callbackExecutor.execute(() -> {
            try {
                pushRecordService.updateCallback(id, callbackResult);
                logger.info("Callback processed successfully, id: {}, callbackId: {}", id, callbackId);
            } catch (Exception e) {
                logger.error("Callback processing failed, id: {}, callbackId: {}", id, callbackId, e);
                if (callbackId != null) {
                    callbackIdempotentService.removeProcessed(callbackId);
                }
            }
        });

        return Result.success(true);
    }

    @PostMapping("/callback/sync/{id}")
    public Result<Boolean> callbackSync(@PathVariable Long id,
                                        @RequestHeader(value = "X-Callback-Id", required = false) String callbackId,
                                        @RequestBody String callbackResult) {
        if (callbackId != null && !callbackId.isEmpty()) {
            if (callbackIdempotentService.isProcessed(callbackId)) {
                logger.info("Duplicate callback detected, id: {}, callbackId: {}", id, callbackId);
                return Result.success(true);
            }
        }

        logger.info("Processing callback sync, id: {}, callbackId: {}", id, callbackId);
        
        boolean success = pushRecordService.updateCallback(id, callbackResult);
        
        if (success && callbackId != null) {
            callbackIdempotentService.markProcessed(callbackId);
        }

        return Result.success(success);
    }
}
