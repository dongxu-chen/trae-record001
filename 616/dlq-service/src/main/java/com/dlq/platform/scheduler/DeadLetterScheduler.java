package com.dlq.platform.scheduler;

import com.dlq.platform.analysis.service.DeadLetterAnalysisService;
import com.dlq.platform.common.dto.DeadLetterAnalysisResult;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.service.DeadLetterEsService;
import com.dlq.platform.service.AlertService;
import com.dlq.platform.service.ArchiveService;
import com.dlq.platform.service.DeadLetterConsumeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class DeadLetterScheduler {

    private final DeadLetterConsumeService consumeService;
    private final DeadLetterAnalysisService analysisService;
    private final DeadLetterEsService deadLetterEsService;
    private final AlertService alertService;
    private final ArchiveService archiveService;

    @Value("${dlq.schedule.consume-check.enabled:true}")
    private boolean consumeCheckEnabled;

    @Value("${dlq.schedule.auto-archive.enabled:true}")
    private boolean autoArchiveEnabled;

    @Value("${dlq.schedule.alert-check.enabled:true}")
    private boolean alertCheckEnabled;

    @Value("${dlq.schedule.statistics.enabled:true}")
    private boolean statisticsEnabled;

    @Value("${dlq.schedule.clean-archive.enabled:true}")
    private boolean cleanArchiveEnabled;

    @Scheduled(fixedDelayString = "${dlq.schedule.consume-check.interval:60000}")
    public void consumeHealthCheck() {
        if (!consumeCheckEnabled) {
            return;
        }

        try {
            log.debug("开始执行消费者健康检查...");

            Map<String, Boolean> consumerStatus = consumeService.getConsumerStatus();

            for (Map.Entry<String, Boolean> entry : consumerStatus.entrySet()) {
                if (!Boolean.TRUE.equals(entry.getValue())) {
                    log.warn("消费者 {} 状态异常，尝试重启...", entry.getKey());
                    try {
                        consumeService.restartConsumer(entry.getKey());
                        log.info("消费者 {} 重启成功", entry.getKey());
                    } catch (Exception e) {
                        log.error("重启消费者 {} 失败", entry.getKey(), e);
                    }
                }
            }

            log.debug("消费者健康检查完成, 状态: {}", consumerStatus);
        } catch (Exception e) {
            log.error("消费者健康检查异常", e);
        }
    }

    @Scheduled(cron = "${dlq.schedule.auto-archive.cron:0 0 2 * * ?}")
    public void autoArchive() {
        if (!autoArchiveEnabled) {
            return;
        }

        try {
            log.info("开始执行自动归档任务...");

            int archivedCount = archiveService.autoArchive();

            log.info("自动归档任务完成, 归档数量: {}", archivedCount);
        } catch (Exception e) {
            log.error("自动归档任务异常", e);
        }
    }

    @Scheduled(fixedDelayString = "${dlq.schedule.alert-check.interval:300000}")
    public void alertCheck() {
        if (!alertCheckEnabled) {
            return;
        }

        try {
            log.debug("开始执行告警检测任务...");

            DeadLetterQueryDTO queryDTO = new DeadLetterQueryDTO();
            queryDTO.setProcessStatus(ProcessStatusEnum.PENDING);
            queryDTO.setPageSize(1000);

            List<DeadLetterMessage> pendingMessages = deadLetterEsService.queryForList(queryDTO);

            if (pendingMessages.isEmpty()) {
                log.debug("告警检测任务完成, 没有待处理的死信消息");
                return;
            }

            List<DeadLetterAnalysisResult> analysisResults = analysisService.analyzeBatch(pendingMessages);
            Map<String, DeadLetterAnalysisResult> resultMap = new HashMap<>();
            for (DeadLetterAnalysisResult result : analysisResults) {
                if (result.getMessageId() != null) {
                    resultMap.put(result.getMessageId(), result);
                }
            }

            alertService.checkAlertsForMessages(pendingMessages, resultMap);

            log.debug("告警检测任务完成, 检测消息数量: {}", pendingMessages.size());
        } catch (Exception e) {
            log.error("告警检测任务异常", e);
        }
    }

    @Scheduled(cron = "${dlq.schedule.statistics.cron:0 */5 * * * ?}")
    public void statisticsTask() {
        if (!statisticsEnabled) {
            return;
        }

        try {
            log.debug("开始执行死信统计任务...");

            Map<String, Object> stats = deadLetterEsService.getStatistics();

            log.info("死信统计任务完成, 总数: {}, 今日新增: {}, 待处理: {}",
                    stats.get("totalCount"),
                    stats.get("todayNewCount"),
                    stats.get("statusDistribution"));

        } catch (Exception e) {
            log.error("死信统计任务异常", e);
        }
    }

    @Scheduled(cron = "${dlq.schedule.clean-archive.cron:0 0 3 * * ?}")
    public void cleanExpiredArchive() {
        if (!cleanArchiveEnabled) {
            return;
        }

        try {
            log.info("开始执行归档清理任务...");

            int result = archiveService.cleanExpiredArchive();

            log.info("归档清理任务完成, 结果: {}", result);
        } catch (Exception e) {
            log.error("归档清理任务异常", e);
        }
    }

    @Scheduled(fixedDelayString = "${dlq.schedule.reprocess.interval:600000}")
    public void reprocessPendingMessages() {
        if (!consumeCheckEnabled) {
            return;
        }

        try {
            log.debug("开始执行待处理消息重新消费任务...");

            DeadLetterQueryDTO queryDTO = new DeadLetterQueryDTO();
            queryDTO.setProcessStatus(ProcessStatusEnum.PENDING);
            queryDTO.setEndTime(LocalDateTime.now().minusMinutes(10));
            queryDTO.setPageSize(100);

            List<DeadLetterMessage> pendingMessages = deadLetterEsService.queryForList(queryDTO);

            if (pendingMessages.isEmpty()) {
                log.debug("重新消费任务完成, 没有需要重新处理的消息");
                return;
            }

            log.info("发现 {} 条待处理消息，开始重新处理...", pendingMessages.size());

            for (DeadLetterMessage message : pendingMessages) {
                try {
                    consumeService.processDeadLetter(message);
                } catch (Exception e) {
                    log.error("重新处理消息失败, messageId: {}", message.getId(), e);
                }
            }

            log.info("待处理消息重新消费任务完成, 处理数量: {}", pendingMessages.size());
        } catch (Exception e) {
            log.error("待处理消息重新消费任务异常", e);
        }
    }
}
