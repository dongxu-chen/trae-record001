package com.dlq.platform.api.controller;

import com.dlq.platform.api.common.PageResult;
import com.dlq.platform.api.common.Result;
import com.dlq.platform.common.dto.ArchiveRequest;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.dto.ReplayRequest;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.service.DeadLetterService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/dead-letters")
@RequiredArgsConstructor
public class DeadLetterController {

    private final DeadLetterService deadLetterService;

    @GetMapping
    public Result<Map<String, Object>> list(
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(required = false) String topic,
            @RequestParam(required = false) String queueName,
            @RequestParam(required = false) String messageId,
            @RequestParam(required = false) DeadReasonTypeEnum deadReasonType,
            @RequestParam(required = false) ProcessStatusEnum processStatus,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {

        DeadLetterQueryDTO query = DeadLetterQueryDTO.builder()
                .mqType(mqType)
                .topic(topic)
                .queueName(queueName)
                .messageId(messageId)
                .deadReasonType(deadReasonType)
                .processStatus(processStatus)
                .startTime(startTime)
                .endTime(endTime)
                .pageNum(pageNum)
                .pageSize(pageSize)
                .build();

        Map<String, Object> page = deadLetterService.queryDeadLetters(query);
        return Result.success(page);
    }

    @GetMapping("/{id}")
    public Result<DeadLetterMessage> getById(@PathVariable String id) {
        DeadLetterMessage message = deadLetterService.getDeadLetterDetail(id);
        return Result.success(message);
    }

    @PostMapping("/{id}/replay")
    public Result<Map<String, Object>> replay(@PathVariable String id, @RequestBody(required = false) ReplayRequest request) {
        Map<String, Object> result = deadLetterService.replaySingle(id, request);
        return Result.success(result);
    }

    @PostMapping("/batch-replay")
    public Result<Map<String, Object>> batchReplay(@Valid @RequestBody ReplayRequest request) {
        Map<String, Object> result = deadLetterService.batchReplay(request);
        return Result.success(result);
    }

    @PostMapping("/{id}/archive")
    public Result<Map<String, Object>> archive(@PathVariable String id, @RequestBody(required = false) ArchiveRequest request) {
        Map<String, Object> result = deadLetterService.batchArchive(request != null ? request : new ArchiveRequest());
        if (request != null) {
            request.setIds(List.of(id));
        }
        return Result.success(result);
    }

    @PostMapping("/batch-archive")
    public Result<Map<String, Object>> batchArchive(@Valid @RequestBody ArchiveRequest request) {
        Map<String, Object> result = deadLetterService.batchArchive(request);
        return Result.success(result);
    }

    @PostMapping("/{id}/ignore")
    public Result<Map<String, Object>> ignore(@PathVariable String id, @RequestParam(required = false) String remark) {
        Map<String, Object> result = deadLetterService.ignoreDeadLetter(id, "system", remark);
        return Result.success(result);
    }

    @PostMapping("/batch-ignore")
    public Result<Map<String, Object>> batchIgnore(
            @RequestBody @NotEmpty(message = "消息ID列表不能为空") List<String> ids,
            @RequestParam(required = false) String remark) {
        Map<String, Object> result = deadLetterService.batchIgnore(ids, "system", remark);
        return Result.success(result);
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> statistics() {
        Map<String, Object> statistics = deadLetterService.getStatistics();
        return Result.success(statistics);
    }

    @GetMapping("/aggregation")
    public Result<Map<String, Object>> aggregation(
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(required = false) String groupBy,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime) {
        DeadLetterQueryDTO query = DeadLetterQueryDTO.builder()
                .mqType(mqType)
                .startTime(startTime)
                .endTime(endTime)
                .build();
        Map<String, Object> aggregation = deadLetterService.queryDeadLetters(query);
        return Result.success(aggregation);
    }
}
