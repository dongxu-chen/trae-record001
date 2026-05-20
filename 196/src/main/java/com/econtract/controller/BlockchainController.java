package com.econtract.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.econtract.common.Result;
import com.econtract.entity.BlockchainBatch;
import com.econtract.entity.BlockchainEvidence;
import com.econtract.service.BlockchainBatchService;
import com.econtract.service.BlockchainService;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/blockchain")
public class BlockchainController {

    @Resource
    private BlockchainService blockchainService;

    @Resource
    private BlockchainBatchService batchService;

    @GetMapping("/evidence/{evidenceNo}")
    public Result<Map<String, Object>> getEvidence(@PathVariable String evidenceNo) {
        return Result.success(blockchainService.getEvidence(evidenceNo));
    }

    @GetMapping("/evidence/list")
    public Result<List<BlockchainEvidence>> getEvidenceList(
            @RequestParam String bizType,
            @RequestParam Long bizId) {
        return Result.success(blockchainService.getEvidenceList(bizType, bizId));
    }

    @PostMapping("/evidence/save")
    public Result<BlockchainEvidence> saveEvidence(
            @RequestParam String bizType,
            @RequestParam Long bizId,
            @RequestBody Object data) {
        return Result.success(blockchainService.saveEvidence(bizType, bizId, data));
    }

    @GetMapping("/batch/page")
    public Result<Page<BlockchainBatch>> getBatchPage(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize) {
        return Result.success(batchService.getBatchPage(pageNum, pageSize));
    }

    @GetMapping("/batch/evidences/{batchNo}")
    public Result<List<BlockchainEvidence>> getEvidencesByBatchNo(@PathVariable String batchNo) {
        return Result.success(batchService.getEvidencesByBatchNo(batchNo));
    }

    @GetMapping("/batch/queue/size")
    public Result<Map<String, Object>> getQueueSize() {
        Map<String, Object> result = new HashMap<>();
        result.put("pendingSize", batchService.getPendingQueueSize());
        return Result.success(result);
    }

    @PostMapping("/batch/flush")
    public Result<Void> flushBatch() {
        batchService.triggerBatch();
        return Result.success("已触发批量打包", null);
    }
}
