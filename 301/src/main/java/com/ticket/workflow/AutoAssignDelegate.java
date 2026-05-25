package com.ticket.workflow;

import com.ticket.entity.User;
import com.ticket.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.flowable.engine.delegate.DelegateExecution;
import org.flowable.engine.delegate.JavaDelegate;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
@RequiredArgsConstructor
public class AutoAssignDelegate implements JavaDelegate {

    private final UserRepository userRepository;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String ROUND_ROBIN_KEY = "ticket:auto_assign:round_robin";

    @Override
    public void execute(DelegateExecution execution) {
        WorkflowContext context = getWorkflowContext(execution);

        Long ticketId = context.getTicketId();
        Long assigneeId = context.getAssigneeId();
        String department = context.getDepartment();

        if (ticketId == null) {
            ticketId = (Long) execution.getVariable("ticketId");
        }
        if (assigneeId == null) {
            assigneeId = (Long) execution.getVariable("assigneeId");
        }
        if (department == null) {
            department = (String) execution.getVariable("department");
        }

        log.debug("开始自动分配工单: {}, 使用全局上下文", ticketId);

        if (assigneeId != null) {
            updateContext(context, execution, "assigned", true);
            updateContext(context, execution, "assignee", assigneeId);
            log.debug("工单 {} 已指定处理人: {}", ticketId, assigneeId);
            return;
        }

        try {
            User assignee = getNextAssignee(department);
            if (assignee != null) {
                updateContext(context, execution, "assignee", assignee.getId());
                updateContext(context, execution, "assigned", true);
                context.setAssigneeId(assignee.getId());
                context.setAssigneeName(assignee.getRealName());
                execution.setVariable(WorkflowContext.KEY, context);
                log.debug("工单 {} 自动分配给: {}", ticketId, assignee.getRealName());
            } else {
                updateContext(context, execution, "assigned", false);
                log.warn("工单 {} 未找到可用处理人，进入手动分配", ticketId);
            }
        } catch (Exception e) {
            log.error("自动分配工单失败: {}", ticketId, e);
            updateContext(context, execution, "assigned", false);
        }
    }

    private WorkflowContext getWorkflowContext(DelegateExecution execution) {
        WorkflowContext context = WorkflowContext.getCurrent();
        if (context.getTicketId() == null) {
            Object contextObj = execution.getVariable(WorkflowContext.KEY);
            if (contextObj instanceof WorkflowContext) {
                context = (WorkflowContext) contextObj;
                WorkflowContext.setCurrent(context);
            } else {
                context = WorkflowContext.fromMap(execution.getVariables());
                WorkflowContext.setCurrent(context);
            }
        }
        return context;
    }

    private void updateContext(WorkflowContext context, DelegateExecution execution, String key, Object value) {
        context.setVariable(key, value);
        execution.setVariable(key, value);
    }

    private User getNextAssignee(String department) {
        List<User> users;
        if (department != null && !department.isEmpty()) {
            users = userRepository.findByDepartmentAndAvailableTrue(department);
        } else {
            users = userRepository.findByAvailableTrue();
        }

        if (users.isEmpty()) {
            return null;
        }

        AtomicInteger counter = (AtomicInteger) redisTemplate.opsForValue().get(ROUND_ROBIN_KEY);
        if (counter == null) {
            counter = new AtomicInteger(0);
        }

        int index = counter.getAndIncrement() % users.size();
        redisTemplate.opsForValue().set(ROUND_ROBIN_KEY, counter);

        return users.get(index);
    }
}
