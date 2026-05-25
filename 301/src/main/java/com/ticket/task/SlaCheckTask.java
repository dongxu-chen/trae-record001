package com.ticket.task;

import com.ticket.entity.Ticket;
import com.ticket.enums.SlaStatus;
import com.ticket.service.TicketService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@RequiredArgsConstructor
public class SlaCheckTask {

    private final TicketService ticketService;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String SLA_CHECK_LOCK = "ticket:sla:check:lock";
    private static final String OVERDUE_NOTICE_KEY = "ticket:sla:overdue:notice:";
    private static final String WARNING_NOTICE_KEY = "ticket:sla:warning:notice:";

    @Value("${ticket.sla.check-interval:60000}")
    private long checkInterval;

    @Scheduled(fixedRateString = "${ticket.sla.check-interval:60000}")
    public void checkSla() {
        Boolean locked = redisTemplate.opsForValue().setIfAbsent(
                SLA_CHECK_LOCK,
                LocalDateTime.now().toString(),
                5,
                TimeUnit.MINUTES
        );

        if (Boolean.FALSE.equals(locked)) {
            log.debug("SLA检查任务正在执行中，跳过本次执行");
            return;
        }

        try {
            log.info("开始执行SLA检查任务");
            List<Ticket> tickets = ticketService.getTicketsForSlaCheck();

            int overdueCount = 0;
            int warningCount = 0;

            for (Ticket ticket : tickets) {
                SlaStatus oldStatus = ticket.getSlaStatus();
                ticketService.updateSlaStatus(ticket);
                SlaStatus newStatus = ticket.getSlaStatus();

                if (newStatus != oldStatus) {
                    if (newStatus == SlaStatus.OVERDUE) {
                        overdueCount++;
                        sendOverdueNotice(ticket);
                    } else if (newStatus == SlaStatus.WARNING) {
                        warningCount++;
                        sendWarningNotice(ticket);
                    }
                }
            }

            log.info("SLA检查任务完成，共检查 {} 个工单，超时 {} 个，预警 {} 个",
                    tickets.size(), overdueCount, warningCount);
        } catch (Exception e) {
            log.error("SLA检查任务执行失败", e);
        } finally {
            redisTemplate.delete(SLA_CHECK_LOCK);
        }
    }

    private void sendOverdueNotice(Ticket ticket) {
        String noticeKey = OVERDUE_NOTICE_KEY + ticket.getId();
        Boolean sent = (Boolean) redisTemplate.opsForValue().get(noticeKey);
        if (Boolean.TRUE.equals(sent)) {
            return;
        }

        log.warn("工单 {} 已超时！工单号: {}, 标题: {}, 处理人: {}, SLA状态: {}",
                ticket.getId(), ticket.getTicketNo(), ticket.getTitle(),
                ticket.getAssignee() != null ? ticket.getAssignee().getRealName() : "未分配",
                ticket.getSlaStatus());

        redisTemplate.opsForValue().set(noticeKey, true, 1, TimeUnit.HOURS);
    }

    private void sendWarningNotice(Ticket ticket) {
        String noticeKey = WARNING_NOTICE_KEY + ticket.getId();
        Boolean sent = (Boolean) redisTemplate.opsForValue().get(noticeKey);
        if (Boolean.TRUE.equals(sent)) {
            return;
        }

        log.warn("工单 {} 即将超时！工单号: {}, 标题: {}, 处理人: {}, 响应截止: {}, 解决截止: {}",
                ticket.getId(), ticket.getTicketNo(), ticket.getTitle(),
                ticket.getAssignee() != null ? ticket.getAssignee().getRealName() : "未分配",
                ticket.getResponseDeadline(), ticket.getResolutionDeadline());

        redisTemplate.opsForValue().set(noticeKey, true, 30, TimeUnit.MINUTES);
    }
}
