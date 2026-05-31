package com.dlq.platform.api.controller;

import com.dlq.platform.api.common.Result;
import com.dlq.platform.common.dto.ArchiveRequest;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.service.ArchiveService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/archives")
@RequiredArgsConstructor
public class ArchiveController {

    private final ArchiveService archiveService;

    @GetMapping
    public Result<Map<String, Object>> list(
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(required = false) String topic,
            @RequestParam(required = false) String messageId,
            @RequestParam(required = false) ProcessStatusEnum processStatus,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime,
            @RequestParam(required = false) String archiveIndex,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {

        DeadLetterQueryDTO query = DeadLetterQueryDTO.builder()
                .mqType(mqType)
                .topic(topic)
                .messageId(messageId)
                .processStatus(processStatus)
                .startTime(startTime)
                .endTime(endTime)
                .pageNum(pageNum)
                .pageSize(pageSize)
                .build();

        Map<String, Object> page = archiveService.searchArchive(query, archiveIndex);
        return Result.success(page);
    }

    @PostMapping("/{id}/restore")
    public Result<Map<String, Object>> restore(
            @PathVariable String id,
            @RequestParam(required = false) String archiveIndex,
            @RequestParam(required = false) String operator) {
        Map<String, Object> result = archiveService.restore(id, archiveIndex);
        return Result.success("恢复成功", result);
    }

    @PostMapping("/batch-restore")
    public Result<Map<String, Object>> batchRestore(@RequestBody ArchiveRequest request) {
        Map<String, Object> result = archiveService.batchRestore(request.getIds(), request.getArchiveIndex());
        return Result.success("批量恢复成功", result);
    }

    @GetMapping("/indexes")
    public Result<List<Map<String, Object>>> indexes(
            @RequestParam(required = false) String prefix,
            @RequestParam(defaultValue = "false") Boolean includeStats) {
        List<Map<String, Object>> indexes = archiveService.listArchiveIndexes(prefix, includeStats);
        return Result.success(indexes);
    }

    @GetMapping("/{id}")
    public Result<DeadLetterMessage> getById(
            @PathVariable String id,
            @RequestParam(required = false) String archiveIndex) {
        DeadLetterMessage message = archiveService.getArchivedById(id, archiveIndex);
        return Result.success(message);
    }
}
