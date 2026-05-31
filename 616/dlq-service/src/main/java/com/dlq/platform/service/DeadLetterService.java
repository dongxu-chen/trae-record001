package com.dlq.platform.service;

import com.dlq.platform.common.dto.ArchiveRequest;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.dto.ReplayRequest;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.service.DeadLetterEsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterService {

    private final DeadLetterEsService deadLetterEsService;
    private final DeadLetterReplayService replayService;
    private final ArchiveService archiveService;

    public Map<String, Object> queryDeadLetters(DeadLetterQueryDTO queryDTO) {
        return deadLetterEsService.query(queryDTO);
    }

    public DeadLetterMessage getDeadLetterDetail(String id) {
        return deadLetterEsService.findById(id);
    }

    public Map<String, Object> ignoreDeadLetter(String id, String operator, String remark) {
        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterMessage message = deadLetterEsService.findById(id);
            if (message == null) {
                result.put("success", false);
                result.put("message", "死信消息不存在, id: " + id);
                return result;
            }

            if (message.getProcessStatus() == ProcessStatusEnum.IGNORED) {
                result.put("success", false);
                result.put("message", "消息已被忽略, id: " + id);
                return result;
            }

            deadLetterEsService.updateStatus(id, ProcessStatusEnum.IGNORED);

            if (message.getHeaders() == null) {
                message.setHeaders(new HashMap<>());
            }
            message.getHeaders().put("ignoreOperator", operator);
            message.getHeaders().put("ignoreRemark", remark);
            message.getHeaders().put("ignoreTime", LocalDateTime.now().toString());
            deadLetterEsService.save(message);

            result.put("success", true);
            result.put("message", "忽略成功");
            result.put("id", id);

            log.info("忽略死信消息成功, id: {}, operator: {}", id, operator);
        } catch (Exception e) {
            log.error("忽略死信消息异常, id: {}", id, e);
            result.put("success", false);
            result.put("message", "忽略异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> markProcessed(String id, String operator, String remark) {
        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterMessage message = deadLetterEsService.findById(id);
            if (message == null) {
                result.put("success", false);
                result.put("message", "死信消息不存在, id: " + id);
                return result;
            }

            if (message.getProcessStatus() == ProcessStatusEnum.PROCESSED) {
                result.put("success", false);
                result.put("message", "消息已标记处理, id: " + id);
                return result;
            }

            deadLetterEsService.updateStatus(id, ProcessStatusEnum.PROCESSED);

            if (message.getHeaders() == null) {
                message.setHeaders(new HashMap<>());
            }
            message.getHeaders().put("processOperator", operator);
            message.getHeaders().put("processRemark", remark);
            message.getHeaders().put("processTime", LocalDateTime.now().toString());
            deadLetterEsService.save(message);

            result.put("success", true);
            result.put("message", "标记处理成功");
            result.put("id", id);

            log.info("标记死信消息处理成功, id: {}, operator: {}", id, operator);
        } catch (Exception e) {
            log.error("标记死信消息处理异常, id: {}", id, e);
            result.put("success", false);
            result.put("message", "标记处理异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> batchIgnore(List<String> ids, String operator, String remark) {
        Map<String, Object> result = new HashMap<>();

        try {
            if (ids == null || ids.isEmpty()) {
                result.put("success", false);
                result.put("message", "消息ID列表不能为空");
                return result;
            }

            List<DeadLetterMessage> messages = deadLetterEsService.findByIds(ids);
            if (messages.isEmpty()) {
                result.put("success", false);
                result.put("message", "未找到有效的死信消息");
                return result;
            }

            List<String> toIgnore = messages.stream()
                    .filter(m -> m.getProcessStatus() != ProcessStatusEnum.IGNORED)
                    .map(DeadLetterMessage::getId)
                    .toList();

            if (toIgnore.isEmpty()) {
                result.put("success", true);
                result.put("message", "所有消息都已被忽略");
                result.put("ignoredCount", 0);
                return result;
            }

            deadLetterEsService.updateStatusBatch(toIgnore, ProcessStatusEnum.IGNORED);

            for (DeadLetterMessage message : messages) {
                if (toIgnore.contains(message.getId())) {
                    if (message.getHeaders() == null) {
                        message.setHeaders(new HashMap<>());
                    }
                    message.getHeaders().put("ignoreOperator", operator);
                    message.getHeaders().put("ignoreRemark", remark);
                    message.getHeaders().put("ignoreTime", LocalDateTime.now().toString());
                    deadLetterEsService.save(message);
                }
            }

            result.put("success", true);
            result.put("totalCount", ids.size());
            result.put("ignoredCount", toIgnore.size());
            result.put("skippedCount", ids.size() - toIgnore.size());

            log.info("批量忽略完成, 总数: {}, 忽略: {}, 跳过: {}", ids.size(), toIgnore.size(), ids.size() - toIgnore.size());
        } catch (Exception e) {
            log.error("批量忽略异常", e);
            result.put("success", false);
            result.put("message", "批量忽略异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> batchMarkProcessed(List<String> ids, String operator, String remark) {
        Map<String, Object> result = new HashMap<>();

        try {
            if (ids == null || ids.isEmpty()) {
                result.put("success", false);
                result.put("message", "消息ID列表不能为空");
                return result;
            }

            List<DeadLetterMessage> messages = deadLetterEsService.findByIds(ids);
            if (messages.isEmpty()) {
                result.put("success", false);
                result.put("message", "未找到有效的死信消息");
                return result;
            }

            List<String> toProcess = messages.stream()
                    .filter(m -> m.getProcessStatus() != ProcessStatusEnum.PROCESSED)
                    .map(DeadLetterMessage::getId)
                    .toList();

            if (toProcess.isEmpty()) {
                result.put("success", true);
                result.put("message", "所有消息都已标记处理");
                result.put("processedCount", 0);
                return result;
            }

            deadLetterEsService.updateStatusBatch(toProcess, ProcessStatusEnum.PROCESSED);

            for (DeadLetterMessage message : messages) {
                if (toProcess.contains(message.getId())) {
                    if (message.getHeaders() == null) {
                        message.setHeaders(new HashMap<>());
                    }
                    message.getHeaders().put("processOperator", operator);
                    message.getHeaders().put("processRemark", remark);
                    message.getHeaders().put("processTime", LocalDateTime.now().toString());
                    deadLetterEsService.save(message);
                }
            }

            result.put("success", true);
            result.put("totalCount", ids.size());
            result.put("processedCount", toProcess.size());
            result.put("skippedCount", ids.size() - toProcess.size());

            log.info("批量标记处理完成, 总数: {}, 处理: {}, 跳过: {}", ids.size(), toProcess.size(), ids.size() - toProcess.size());
        } catch (Exception e) {
            log.error("批量标记处理异常", e);
            result.put("success", false);
            result.put("message", "批量标记处理异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> batchReplay(ReplayRequest request) {
        return replayService.replayBatch(request);
    }

    public Map<String, Object> batchArchive(ArchiveRequest request) {
        return archiveService.archiveBatch(request);
    }

    public Map<String, Object> getStatistics() {
        Map<String, Object> stats = deadLetterEsService.getStatistics();

        Map<String, Long> statusDistribution = (Map<String, Long>) stats.get("statusDistribution");
        if (statusDistribution == null) {
            statusDistribution = new HashMap<>();
        }

        stats.put("pendingCount", statusDistribution.getOrDefault("PENDING", 0L));
        stats.put("processedCount", statusDistribution.getOrDefault("PROCESSED", 0L));
        stats.put("replayedCount", statusDistribution.getOrDefault("REPLAYED", 0L));
        stats.put("archivedCount", statusDistribution.getOrDefault("ARCHIVED", 0L));
        stats.put("ignoredCount", statusDistribution.getOrDefault("IGNORED", 0L));

        stats.put("overviewTime", LocalDateTime.now());

        return stats;
    }

    public Map<String, Object> deleteDeadLetter(String id) {
        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterMessage message = deadLetterEsService.findById(id);
            if (message == null) {
                result.put("success", false);
                result.put("message", "死信消息不存在, id: " + id);
                return result;
            }

            deadLetterEsService.deleteById(id);

            result.put("success", true);
            result.put("message", "删除成功");
            result.put("id", id);

            log.info("删除死信消息成功, id: {}", id);
        } catch (Exception e) {
            log.error("删除死信消息异常, id: {}", id, e);
            result.put("success", false);
            result.put("message", "删除异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> batchDelete(List<String> ids) {
        Map<String, Object> result = new HashMap<>();

        try {
            if (ids == null || ids.isEmpty()) {
                result.put("success", false);
                result.put("message", "消息ID列表不能为空");
                return result;
            }

            deadLetterEsService.deleteByIds(ids);

            result.put("success", true);
            result.put("message", "批量删除成功");
            result.put("count", ids.size());

            log.info("批量删除死信消息成功, 数量: {}", ids.size());
        } catch (Exception e) {
            log.error("批量删除死信消息异常", e);
            result.put("success", false);
            result.put("message", "批量删除异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> replaySingle(String id, ReplayRequest request) {
        return replayService.replaySingle(id, request);
    }
}
