package com.dlq.platform.service;

import com.dlq.platform.common.dto.ArchiveRequest;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.service.ArchiveEsService;
import com.dlq.platform.es.service.DeadLetterEsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ArchiveService {

    private final DeadLetterEsService deadLetterEsService;
    private final ArchiveEsService archiveEsService;

    @Value("${dlq.archive.auto-archive-days:30}")
    private int autoArchiveDays;

    @Value("${dlq.archive.keep-days:90}")
    private int archiveKeepDays;

    public Map<String, Object> archiveById(String id, String operator, String remark) {
        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterMessage message = deadLetterEsService.findById(id);
            if (message == null) {
                result.put("success", false);
                result.put("message", "死信消息不存在, id: " + id);
                return result;
            }

            if (message.getProcessStatus() == ProcessStatusEnum.ARCHIVED) {
                result.put("success", false);
                result.put("message", "消息已归档, id: " + id);
                return result;
            }

            archiveEsService.archive(message);

            result.put("success", true);
            result.put("message", "归档成功");
            result.put("id", id);

            log.info("手动归档成功, id: {}, operator: {}", id, operator);
        } catch (Exception e) {
            log.error("手动归档异常, id: {}", id, e);
            result.put("success", false);
            result.put("message", "归档异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> archiveBatch(ArchiveRequest request) {
        Map<String, Object> result = new HashMap<>();

        try {
            List<String> messageIds = request.getMessageIds();
            if (messageIds == null || messageIds.isEmpty()) {
                result.put("success", false);
                result.put("message", "归档消息ID列表不能为空");
                return result;
            }

            List<DeadLetterMessage> messages = deadLetterEsService.findByIds(messageIds);
            if (messages.isEmpty()) {
                result.put("success", false);
                result.put("message", "未找到有效的死信消息");
                return result;
            }

            List<DeadLetterMessage> toArchive = messages.stream()
                    .filter(m -> m.getProcessStatus() != ProcessStatusEnum.ARCHIVED)
                    .collect(Collectors.toList());

            if (toArchive.isEmpty()) {
                result.put("success", true);
                result.put("message", "所有消息都已归档");
                result.put("archivedCount", 0);
                return result;
            }

            archiveEsService.archiveBatch(toArchive);

            result.put("success", true);
            result.put("totalCount", messages.size());
            result.put("archivedCount", toArchive.size());
            result.put("skippedCount", messages.size() - toArchive.size());

            log.info("批量归档完成, 总数: {}, 归档: {}, 跳过: {}", messages.size(), toArchive.size(), messages.size() - toArchive.size());
        } catch (Exception e) {
            log.error("批量归档异常", e);
            result.put("success", false);
            result.put("message", "批量归档异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> archiveByCondition(ArchiveRequest request) {
        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterQueryDTO queryDTO = convertToQueryDTO(request);
            List<DeadLetterMessage> messages = deadLetterEsService.queryForList(queryDTO);

            if (messages.isEmpty()) {
                result.put("success", true);
                result.put("message", "没有符合条件的死信消息");
                result.put("totalCount", 0);
                return result;
            }

            request.setMessageIds(messages.stream().map(DeadLetterMessage::getId).collect(Collectors.toList()));
            return archiveBatch(request);
        } catch (Exception e) {
            log.error("按条件归档异常", e);
            result.put("success", false);
            result.put("message", "按条件归档异常: " + e.getMessage());
        }

        return result;
    }

    public int autoArchive() {
        try {
            log.info("开始执行自动归档任务, 保留天数: {}天", autoArchiveDays);

            LocalDateTime archiveTime = LocalDateTime.now().minusDays(autoArchiveDays);

            DeadLetterQueryDTO queryDTO = new DeadLetterQueryDTO();
            queryDTO.setProcessStatus(ProcessStatusEnum.PROCESSED);
            queryDTO.setEndTime(archiveTime);
            queryDTO.setPageSize(10000);

            List<DeadLetterMessage> messages = deadLetterEsService.queryForList(queryDTO);

            if (messages.isEmpty()) {
                log.info("自动归档任务完成, 没有需要归档的消息");
                return 0;
            }

            archiveEsService.archiveBatch(messages);

            log.info("自动归档任务完成, 归档数量: {}", messages.size());
            return messages.size();
        } catch (Exception e) {
            log.error("自动归档任务异常", e);
            return 0;
        }
    }

    public Map<String, Object> restore(List<String> ids, String operator) {
        Map<String, Object> result = new HashMap<>();

        try {
            if (ids == null || ids.isEmpty()) {
                result.put("success", false);
                result.put("message", "恢复消息ID列表不能为空");
                return result;
            }

            archiveEsService.restore(ids);

            result.put("success", true);
            result.put("message", "恢复成功");
            result.put("count", ids.size());

            log.info("归档恢复完成, 数量: {}, operator: {}", ids.size(), operator);
        } catch (Exception e) {
            log.error("归档恢复异常", e);
            result.put("success", false);
            result.put("message", "归档恢复异常: " + e.getMessage());
        }

        return result;
    }

    public int cleanExpiredArchive() {
        try {
            log.info("开始执行归档清理任务, 保留天数: {}天", archiveKeepDays);

            archiveEsService.deleteExpiredArchive(archiveKeepDays);

            log.info("归档清理任务完成");
            return 1;
        } catch (Exception e) {
            log.error("归档清理任务异常", e);
            return 0;
        }
    }

    public Map<String, Object> queryArchive(ArchiveRequest request, int pageNum, int pageSize) {
        try {
            return archiveEsService.queryArchive(request, pageNum, pageSize);
        } catch (Exception e) {
            log.error("查询归档列表异常", e);
            throw new RuntimeException("查询归档列表异常", e);
        }
    }

    public DeadLetterMessage getArchiveById(String id) {
        try {
            List<DeadLetterMessage> messages = archiveEsService.findArchiveByIds(Collections.singletonList(id));
            return messages.isEmpty() ? null : messages.get(0);
        } catch (Exception e) {
            log.error("查询归档详情异常, id: {}", id, e);
            throw new RuntimeException("查询归档详情异常", e);
        }
    }

    private DeadLetterQueryDTO convertToQueryDTO(ArchiveRequest request) {
        DeadLetterQueryDTO queryDTO = new DeadLetterQueryDTO();
        queryDTO.setMqType(request.getMqType());
        queryDTO.setTopic(request.getTopic());
        queryDTO.setProcessStatus(request.getProcessStatus());
        queryDTO.setStartTime(request.getStartTime());
        queryDTO.setEndTime(request.getEndTime());
        queryDTO.setPageSize(10000);
        return queryDTO;
    }
}
