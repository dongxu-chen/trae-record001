package com.ticket.service;

import com.ticket.calendar.WorkCalendarService;
import com.ticket.calendar.WorkCalendarConfig;
import com.ticket.dto.AssignTicketDTO;
import com.ticket.dto.CreateRelationDTO;
import com.ticket.dto.CreateTicketDTO;
import com.ticket.dto.TicketQueryDTO;
import com.ticket.dto.UpdateTicketStatusDTO;
import com.ticket.entity.Sla;
import com.ticket.entity.Ticket;
import com.ticket.entity.TicketHistory;
import com.ticket.entity.TicketRelation;
import com.ticket.entity.TicketTemplate;
import com.ticket.entity.User;
import com.ticket.enums.RelationType;
import com.ticket.enums.SlaStatus;
import com.ticket.enums.TicketStatus;
import com.ticket.exception.BusinessException;
import com.ticket.repository.TicketRepository;
import com.ticket.repository.UserRepository;
import com.ticket.vo.TicketVO;
import com.ticket.workflow.TicketWorkflowService;
import com.ticket.workflow.WorkflowContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.RandomStringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

@Slf4j
@Service
@RequiredArgsConstructor
public class TicketService {

    private final TicketRepository ticketRepository;
    private final UserRepository userRepository;
    private final SlaService slaService;
    private final TicketTemplateService templateService;
    private final TicketRelationService relationService;
    private final TicketHistoryService historyService;
    private final TicketWorkflowService workflowService;
    private final WorkCalendarService workCalendarService;
    private final WorkCalendarConfig workCalendarConfig;
    private final RedisTemplate<String, Object> redisTemplate;

    @Value("${ticket.sla.use-work-calendar:true}")
    private boolean useWorkCalendar;

    private static final String TICKET_NO_PREFIX = "TK";
    private static final String TICKET_COUNTER_KEY = "ticket:counter";
    private static final List<TicketStatus> COMPLETED_STATUSES = List.of(
            TicketStatus.COMPLETED, TicketStatus.CLOSED, TicketStatus.CANCELLED
    );

    @Transactional
    public Ticket createTicket(CreateTicketDTO dto) {
        User creator = userRepository.findById(dto.getCreatorId())
                .orElseThrow(() -> new BusinessException("创建人不存在: " + dto.getCreatorId()));

        User assignee = null;
        if (dto.getAssigneeId() != null) {
            assignee = userRepository.findById(dto.getAssigneeId())
                    .orElseThrow(() -> new BusinessException("处理人不存在: " + dto.getAssigneeId()));
        }

        TicketTemplate template = null;
        if (dto.getTemplateId() != null) {
            template = templateService.getTemplateById(dto.getTemplateId());
            if (assignee == null && template.getDefaultAssignee() != null) {
                assignee = template.getDefaultAssignee();
            }
        }

        Ticket ticket = new Ticket();
        ticket.setTicketNo(generateTicketNo());
        ticket.setTitle(dto.getTitle());
        ticket.setTicketType(dto.getTicketType());
        ticket.setPriority(dto.getPriority());
        ticket.setStatus(TicketStatus.PENDING);
        ticket.setDescription(dto.getDescription());
        ticket.setCreator(creator);
        ticket.setAssignee(assignee);
        ticket.setCustomFields(dto.getCustomFields());

        if (assignee != null) {
            ticket.setStatus(TicketStatus.ASSIGNED);
        }

        Optional<Sla> slaOpt = slaService.findMatchingSla(dto.getTicketType(), dto.getPriority());
        slaOpt.ifPresent(sla -> {
            ticket.setSla(sla);
            ticket.setResponseDeadline(calculateDeadline(sla.getResponseTime()));
            ticket.setResolutionDeadline(calculateDeadline(sla.getResolutionTime()));
        });

        if (template != null && template.getSla() != null && slaOpt.isEmpty()) {
            Sla templateSla = template.getSla();
            ticket.setSla(templateSla);
            ticket.setResponseDeadline(calculateDeadline(templateSla.getResponseTime()));
            ticket.setResolutionDeadline(calculateDeadline(templateSla.getResolutionTime()));
        }

        ticket = ticketRepository.save(ticket);

        WorkflowContext context = buildWorkflowContext(ticket, assignee);
        workflowService.startProcess(ticket, assignee, context);

        historyService.addStatusChangeHistory(ticket, null, ticket.getStatus(), "创建工单", creator.getId());

        if (dto.getParentTicketId() != null) {
            CreateRelationDTO relationDTO = new CreateRelationDTO();
            relationDTO.setSourceTicketId(dto.getParentTicketId());
            relationDTO.setTargetTicketId(ticket.getId());
            relationDTO.setRelationType(RelationType.PARENT_CHILD);
            relationDTO.setCreatedById(creator.getId());
            relationService.createRelation(relationDTO);

            updateParentTicketProgress(dto.getParentTicketId());
        }

        log.info("工单创建成功: {}, 工单号: {}", ticket.getId(), ticket.getTicketNo());
        return ticket;
    }

    private LocalDateTime calculateDeadline(int minutes) {
        LocalDateTime now = LocalDateTime.now();
        if (useWorkCalendar && workCalendarConfig.isEnabled()) {
            return workCalendarService.calculateDeadline(now, minutes);
        } else {
            return now.plusMinutes(minutes);
        }
    }

    private WorkflowContext buildWorkflowContext(Ticket ticket, User assignee) {
        WorkflowContext context = WorkflowContext.create();
        context.setTicketId(ticket.getId());
        context.setTicketNo(ticket.getTicketNo());
        context.setTitle(ticket.getTitle());
        context.setCreatorId(ticket.getCreator().getId());
        context.setCreatorName(ticket.getCreator().getRealName());
        context.setTicketType(ticket.getTicketType().name());
        context.setPriority(ticket.getPriority().name());
        context.setStatus(ticket.getStatus().name());
        context.setResponseDeadline(ticket.getResponseDeadline());
        context.setResolutionDeadline(ticket.getResolutionDeadline());
        context.setCreatedAt(ticket.getCreatedAt());
        context.setCustomFields(ticket.getCustomFields());
        if (ticket.getSla() != null) {
            context.setSlaId(ticket.getSla().getId());
        }
        if (assignee != null) {
            context.setAssigneeId(assignee.getId());
            context.setAssigneeName(assignee.getRealName());
            context.setDepartment(assignee.getDepartment());
        }
        if (ticket.getProcessInstanceId() != null) {
            context.setProcessInstanceId(ticket.getProcessInstanceId());
        }
        return context;
    }

    private String generateTicketNo() {
        String datePart = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        Long counter = redisTemplate.opsForValue().increment(TICKET_COUNTER_KEY);
        if (counter == 1) {
            redisTemplate.expireAt(TICKET_COUNTER_KEY,
                    LocalDateTime.now().plusDays(1).withHour(0).withMinute(0).withSecond(0));
        }
        String randomPart = RandomStringUtils.randomAlphanumeric(4).toUpperCase();
        return String.format("%s%s%05d%s", TICKET_NO_PREFIX, datePart, counter, randomPart);
    }

    @Transactional
    public Ticket assignTicket(AssignTicketDTO dto) {
        Ticket ticket = getTicketById(dto.getTicketId());

        if (dto.getAutoAssign()) {
            throw new BusinessException("自动分配请使用工作流");
        }

        User assignee = userRepository.findById(dto.getAssigneeId())
                .orElseThrow(() -> new BusinessException("处理人不存在: " + dto.getAssigneeId()));

        TicketStatus oldStatus = ticket.getStatus();
        ticket.setAssignee(assignee);
        ticket.setStatus(TicketStatus.ASSIGNED);
        ticket = ticketRepository.save(ticket);

        WorkflowContext context = buildWorkflowContext(ticket, assignee);
        context.setVariable("assignee", assignee.getId());
        context.setVariable("assigned", true);
        workflowService.completeTaskWithContext(ticket.getProcessInstanceId(), dto.getOperatorId(), context);

        historyService.addStatusChangeHistory(ticket, oldStatus, ticket.getStatus(),
                dto.getRemark(), dto.getOperatorId());

        log.info("工单 {} 已分配给: {}", ticket.getTicketNo(), assignee.getRealName());
        return ticket;
    }

    @Transactional
    public Ticket updateStatus(UpdateTicketStatusDTO dto) {
        Ticket ticket = getTicketById(dto.getTicketId());
        TicketStatus oldStatus = ticket.getStatus();
        TicketStatus targetStatus = dto.getTargetStatus();

        validateStatusTransition(oldStatus, targetStatus);

        boolean wasNotCompleted = !COMPLETED_STATUSES.contains(oldStatus);
        boolean isNowCompleted = COMPLETED_STATUSES.contains(targetStatus);

        ticket.setStatus(targetStatus);

        switch (targetStatus) {
            case IN_PROGRESS:
                if (ticket.getRespondedAt() == null) {
                    ticket.setRespondedAt(LocalDateTime.now());
                }
                break;
            case RESOLVED:
                ticket.setResolvedAt(LocalDateTime.now());
                ticket.setResolution(dto.getResolution());
                break;
            case COMPLETED:
            case CLOSED:
                ticket.setResolvedAt(ticket.getResolvedAt() != null ? ticket.getResolvedAt() : LocalDateTime.now());
                updateSlaStatusOnComplete(ticket);
                break;
            default:
                break;
        }

        ticket = ticketRepository.save(ticket);

        WorkflowContext context = buildWorkflowContext(ticket, ticket.getAssignee());
        switch (targetStatus) {
            case IN_PROGRESS:
                context.setVariable("resolved", false);
                break;
            case PENDING_REPLY:
                context.setVariable("resolved", false);
                break;
            case RESOLVED:
                context.setVariable("resolved", true);
                break;
            case COMPLETED:
                context.setVariable("confirmed", true);
                break;
            case CLOSED:
                context.setVariable("confirmed", true);
                break;
            default:
                break;
        }

        if (ticket.getProcessInstanceId() != null) {
            try {
                workflowService.completeTaskWithContext(ticket.getProcessInstanceId(), dto.getOperatorId(), context);
            } catch (Exception e) {
                log.warn("完成工作流任务失败: {}", e.getMessage());
            }
        }

        historyService.addStatusChangeHistory(ticket, oldStatus, targetStatus,
                dto.getRemark(), dto.getOperatorId());

        if (wasNotCompleted && isNowCompleted) {
            onTicketCompleted(ticket, dto.getOperatorId());
        } else {
            notifyParentTickets(ticket);
        }

        log.info("工单 {} 状态变更: {} -> {}", ticket.getTicketNo(), oldStatus, targetStatus);
        return ticket;
    }

    private void onTicketCompleted(Ticket ticket, Long operatorId) {
        log.info("工单 {} 已完成，触发子工单完成回调", ticket.getTicketNo());

        historyService.addHistory(ticket, "工单完成", "子工单完成，通知父工单更新进度", operatorId);

        notifyParentTickets(ticket);
    }

    private void notifyParentTickets(Ticket childTicket) {
        List<TicketRelation> parentRelations = relationService.getParentTickets(childTicket.getId());

        for (TicketRelation relation : parentRelations) {
            Ticket parentTicket = relation.getSourceTicket();
            if (parentTicket != null && !COMPLETED_STATUSES.contains(parentTicket.getStatus())) {
                try {
                    updateParentTicketProgress(parentTicket, childTicket);
                } catch (Exception e) {
                    log.error("更新父工单进度失败: 父工单={}, 子工单={}", parentTicket.getId(), childTicket.getId(), e);
                }
            }
        }
    }

    private void updateParentTicketProgress(Long parentId) {
        Ticket parent = getTicketById(parentId);
        updateParentTicketProgress(parent, null);
    }

    @Transactional
    public void updateParentTicketProgress(Ticket parent, Ticket changedChild) {
        if (COMPLETED_STATUSES.contains(parent.getStatus())) {
            return;
        }

        List<TicketRelation> childRelations = relationService.getChildTickets(parent.getId());
        if (childRelations.isEmpty()) {
            log.debug("父工单 {} 没有子工单", parent.getTicketNo());
            return;
        }

        int totalChildren = childRelations.size();
        int completedChildren = 0;
        int inProgressChildren = 0;

        Set<String> completedTickets = new HashSet<>();
        Set<String> inProgressTickets = new HashSet<>();

        for (TicketRelation relation : childRelations) {
            Ticket child = relation.getTargetTicket();
            if (child == null) {
                continue;
            }

            TicketStatus childStatus = child.getStatus();
            if (COMPLETED_STATUSES.contains(childStatus)) {
                completedChildren++;
                completedTickets.add(child.getTicketNo());
            } else if (childStatus != TicketStatus.PENDING && childStatus != TicketStatus.CANCELLED) {
                inProgressChildren++;
                inProgressTickets.add(child.getTicketNo());
            }
        }

        double progress = (double) completedChildren / totalChildren * 100;
        String progressStr = String.format("%.1f", progress);

        String progressField = String.format("{\"total\":%d,\"completed\":%d,\"inProgress\":%d,\"progress\":%.2f}",
                totalChildren, completedChildren, inProgressChildren, progress);

        parent.setCustomFields(progressField);
        ticketRepository.save(parent);

        String changeMsg = "";
        if (changedChild != null) {
            changeMsg = String.format("子工单[%s]状态变为[%s]; ",
                    changedChild.getTicketNo(), changedChild.getStatus().getName());
        }

        String remark = String.format("%s进度更新: %d/%d (%.1f%%)%n已完成: %s%n处理中: %s",
                changeMsg,
                completedChildren, totalChildren, progress,
                completedTickets.isEmpty() ? "无" : completedTickets,
                inProgressTickets.isEmpty() ? "无" : inProgressTickets);

        historyService.addHistory(parent, "子工单进度更新", remark, null);

        log.info("父工单 {} 进度更新: {}/{} ({}%)", parent.getTicketNo(), completedChildren, totalChildren, progressStr);

        if (completedChildren == totalChildren) {
            onAllChildrenCompleted(parent);
        }
    }

    private void onAllChildrenCompleted(Ticket parent) {
        log.info("父工单 {} 所有子工单已完成", parent.getTicketNo());

        if (parent.getStatus() == TicketStatus.RESOLVED) {
            historyService.addHistory(parent, "所有子工单完成",
                    "所有子工单已完成，可进行最终确认", null);
        }
    }

    public Map<String, Object> getTicketProgress(Long ticketId) {
        Ticket ticket = getTicketById(ticketId);
        List<TicketRelation> childRelations = relationService.getChildTickets(ticketId);

        Map<String, Object> result = new HashMap<>();
        result.put("totalChildren", childRelations.size());

        int completedChildren = 0;
        int inProgressChildren = 0;
        int pendingChildren = 0;
        List<Map<String, Object>> childDetails = new ArrayList<>();

        for (TicketRelation relation : childRelations) {
            Ticket child = relation.getTargetTicket();
            if (child == null) {
                continue;
            }

            Map<String, Object> childMap = new HashMap<>();
            childMap.put("id", child.getId());
            childMap.put("ticketNo", child.getTicketNo());
            childMap.put("title", child.getTitle());
            childMap.put("status", child.getStatus());
            childMap.put("statusName", child.getStatus().getName());
            childMap.put("assignee", child.getAssignee() != null ? child.getAssignee().getRealName() : null);
            childDetails.add(childMap);

            TicketStatus status = child.getStatus();
            if (COMPLETED_STATUSES.contains(status)) {
                completedChildren++;
            } else if (status == TicketStatus.PENDING) {
                pendingChildren++;
            } else if (status != TicketStatus.CANCELLED) {
                inProgressChildren++;
            }
        }

        double progress = childRelations.size() > 0
                ? (double) completedChildren / childRelations.size() * 100
                : 100.0;

        result.put("completedChildren", completedChildren);
        result.put("inProgressChildren", inProgressChildren);
        result.put("pendingChildren", pendingChildren);
        result.put("progress", progress);
        result.put("children", childDetails);

        return result;
    }

    private void validateStatusTransition(TicketStatus from, TicketStatus to) {
        switch (from) {
            case PENDING:
                if (to != TicketStatus.ASSIGNED && to != TicketStatus.CANCELLED) {
                    throw new BusinessException("待处理工单只能分配或取消");
                }
                break;
            case ASSIGNED:
                if (to != TicketStatus.IN_PROGRESS && to != TicketStatus.PENDING && to != TicketStatus.CANCELLED) {
                    throw new BusinessException("已分配工单只能开始处理、退回待处理或取消");
                }
                break;
            case IN_PROGRESS:
                if (to != TicketStatus.PENDING_REPLY && to != TicketStatus.RESOLVED && to != TicketStatus.ASSIGNED) {
                    throw new BusinessException("处理中工单只能待回复、已解决或退回");
                }
                break;
            case PENDING_REPLY:
                if (to != TicketStatus.IN_PROGRESS && to != TicketStatus.RESOLVED) {
                    throw new BusinessException("待回复工单只能继续处理或标记解决");
                }
                break;
            case RESOLVED:
                if (to != TicketStatus.COMPLETED && to != TicketStatus.IN_PROGRESS) {
                    throw new BusinessException("已解决工单只能完成或重新处理");
                }
                break;
            case COMPLETED:
                if (to != TicketStatus.CLOSED) {
                    throw new BusinessException("已完成工单只能关闭");
                }
                break;
            case CLOSED:
            case CANCELLED:
                throw new BusinessException("已关闭或已取消的工单不能变更状态");
            default:
                break;
        }
    }

    private void updateSlaStatusOnComplete(Ticket ticket) {
        if (ticket.getSla() == null) {
            return;
        }

        SlaStatus slaStatus = SlaStatus.MET;
        LocalDateTime now = LocalDateTime.now();

        if (ticket.getResponseDeadline() != null &&
            ticket.getRespondedAt() != null &&
            ticket.getRespondedAt().isAfter(ticket.getResponseDeadline())) {
            slaStatus = SlaStatus.VIOLATED;
        }

        if (ticket.getResolutionDeadline() != null && now.isAfter(ticket.getResolutionDeadline())) {
            slaStatus = SlaStatus.VIOLATED;
        }

        ticket.setSlaStatus(slaStatus);
    }

    public Ticket getTicketById(Long id) {
        return ticketRepository.findById(id)
                .orElseThrow(() -> new BusinessException("工单不存在: " + id));
    }

    public Ticket getTicketByNo(String ticketNo) {
        return ticketRepository.findByTicketNo(ticketNo)
                .orElseThrow(() -> new BusinessException("工单不存在: " + ticketNo));
    }

    public TicketVO getTicketVOById(Long id) {
        Ticket ticket = getTicketById(id);
        return convertToVO(ticket);
    }

    public Page<TicketVO> getTicketList(TicketQueryDTO dto) {
        Sort.Direction direction = "asc".equalsIgnoreCase(dto.getSortOrder())
                ? Sort.Direction.ASC : Sort.Direction.DESC;
        Pageable pageable = PageRequest.of(
                dto.getPageNum() - 1,
                dto.getPageSize(),
                Sort.by(direction, dto.getSortBy())
        );

        Page<Ticket> ticketPage = ticketRepository.findByConditions(
                dto.getTitle(),
                dto.getStatus(),
                dto.getPriority(),
                dto.getTicketType(),
                dto.getAssigneeId(),
                pageable
        );

        return ticketPage.map(this::convertToVO);
    }

    public Page<TicketVO> getMyCreatedTickets(Long creatorId, Pageable pageable) {
        return ticketRepository.findByCreatorId(creatorId, pageable)
                .map(this::convertToVO);
    }

    public Page<TicketVO> getMyAssignedTickets(Long assigneeId, Pageable pageable) {
        return ticketRepository.findByAssigneeId(assigneeId, pageable)
                .map(this::convertToVO);
    }

    private TicketVO convertToVO(Ticket ticket) {
        TicketVO vo = new TicketVO();
        BeanUtils.copyProperties(ticket, vo);

        if (ticket.getCreator() != null) {
            vo.setCreatorId(ticket.getCreator().getId());
            vo.setCreatorName(ticket.getCreator().getRealName());
        }

        if (ticket.getAssignee() != null) {
            vo.setAssigneeId(ticket.getAssignee().getId());
            vo.setAssigneeName(ticket.getAssignee().getRealName());
        }

        return vo;
    }

    public Map<String, Object> getTicketStatistics() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("pending", ticketRepository.countByStatus(TicketStatus.PENDING));
        stats.put("assigned", ticketRepository.countByStatus(TicketStatus.ASSIGNED));
        stats.put("inProgress", ticketRepository.countByStatus(TicketStatus.IN_PROGRESS));
        stats.put("pendingReply", ticketRepository.countByStatus(TicketStatus.PENDING_REPLY));
        stats.put("resolved", ticketRepository.countByStatus(TicketStatus.RESOLVED));
        stats.put("completed", ticketRepository.countByStatus(TicketStatus.COMPLETED));
        stats.put("closed", ticketRepository.countByStatus(TicketStatus.CLOSED));
        return stats;
    }

    public Map<String, Object> getUserTicketStatistics(Long userId) {
        Map<String, Object> stats = new HashMap<>();
        stats.put("pending", ticketRepository.countByAssigneeIdAndStatus(userId, TicketStatus.PENDING));
        stats.put("assigned", ticketRepository.countByAssigneeIdAndStatus(userId, TicketStatus.ASSIGNED));
        stats.put("inProgress", ticketRepository.countByAssigneeIdAndStatus(userId, TicketStatus.IN_PROGRESS));
        stats.put("pendingReply", ticketRepository.countByAssigneeIdAndStatus(userId, TicketStatus.PENDING_REPLY));
        stats.put("resolved", ticketRepository.countByAssigneeIdAndStatus(userId, TicketStatus.RESOLVED));
        return stats;
    }

    @Transactional
    public void updateSlaStatus(Ticket ticket) {
        if (ticket.getSla() == null || ticket.getSlaStatus() == SlaStatus.MET
                || ticket.getSlaStatus() == SlaStatus.VIOLATED) {
            return;
        }

        LocalDateTime now = LocalDateTime.now();
        SlaStatus newStatus = SlaStatus.NORMAL;
        Sla sla = ticket.getSla();

        boolean responseOverdue = isOverdue(ticket.getResponseDeadline(), ticket.getRespondedAt(), now);
        boolean resolutionOverdue = isOverdue(ticket.getResolutionDeadline(), null, now);

        if (responseOverdue || resolutionOverdue) {
            newStatus = SlaStatus.OVERDUE;
        } else {
            int warningThreshold = sla.getWarningThreshold() != null ? sla.getWarningThreshold() : 30;
            boolean responseWarning = isWarning(ticket.getResponseDeadline(), ticket.getRespondedAt(),
                    now, warningThreshold);
            boolean resolutionWarning = isWarning(ticket.getResolutionDeadline(), null,
                    now, warningThreshold);

            if (responseWarning || resolutionWarning) {
                newStatus = SlaStatus.WARNING;
            }
        }

        if (newStatus != ticket.getSlaStatus()) {
            ticket.setSlaStatus(newStatus);
            ticketRepository.save(ticket);
            log.info("工单 {} SLA状态变更: {} -> {}", ticket.getTicketNo(), ticket.getSlaStatus(), newStatus);
        }
    }

    private boolean isOverdue(LocalDateTime deadline, LocalDateTime completedAt, LocalDateTime now) {
        if (deadline == null) {
            return false;
        }
        if (completedAt != null) {
            if (useWorkCalendar && workCalendarConfig.isEnabled()) {
                return workCalendarService.calculateWorkMinutes(deadline, completedAt) < 0;
            } else {
                return completedAt.isAfter(deadline);
            }
        }
        if (useWorkCalendar && workCalendarConfig.isEnabled()) {
            return workCalendarService.calculateWorkMinutes(deadline, now) < 0;
        } else {
            return now.isAfter(deadline);
        }
    }

    private boolean isWarning(LocalDateTime deadline, LocalDateTime completedAt,
                              LocalDateTime now, int warningThreshold) {
        if (deadline == null || completedAt != null) {
            return false;
        }
        if (useWorkCalendar && workCalendarConfig.isEnabled()) {
            long remainingMinutes = workCalendarService.calculateWorkMinutes(now, deadline);
            return remainingMinutes > 0 && remainingMinutes <= warningThreshold;
        } else {
            LocalDateTime warningTime = now.plusMinutes(warningThreshold);
            return warningTime.isAfter(deadline);
        }
    }

    public List<Ticket> getTicketsForSlaCheck() {
        List<TicketStatus> activeStatuses = List.of(
                TicketStatus.PENDING,
                TicketStatus.ASSIGNED,
                TicketStatus.IN_PROGRESS,
                TicketStatus.PENDING_REPLY,
                TicketStatus.RESOLVED
        );
        List<SlaStatus> finalStatuses = List.of(SlaStatus.MET, SlaStatus.VIOLATED);
        return ticketRepository.findByStatusInAndSlaStatusNotIn(activeStatuses, finalStatuses);
    }
}
