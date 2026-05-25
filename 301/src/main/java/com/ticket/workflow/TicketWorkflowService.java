package com.ticket.workflow;

import com.ticket.entity.Ticket;
import com.ticket.entity.User;
import com.ticket.exception.BusinessException;
import com.ticket.repository.TicketRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.flowable.engine.RuntimeService;
import org.flowable.engine.TaskService;
import org.flowable.engine.runtime.ProcessInstance;
import org.flowable.task.api.Task;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class TicketWorkflowService {

    private final RuntimeService runtimeService;
    private final TaskService taskService;
    private final TicketRepository ticketRepository;

    @Transactional
    public String startProcess(Ticket ticket, User assignee) {
        Map<String, Object> variables = new HashMap<>();
        variables.put("ticketId", ticket.getId());
        variables.put("ticketNo", ticket.getTicketNo());
        variables.put("creator", ticket.getCreator().getId());
        variables.put("assigneeId", assignee != null ? assignee.getId() : null);
        variables.put("assignee", assignee != null ? assignee.getId() : null);
        variables.put("assigned", assignee != null);
        variables.put("resolved", false);
        variables.put("confirmed", false);

        ProcessInstance processInstance = runtimeService.startProcessInstanceByKey(
                "ticketWorkflow",
                ticket.getTicketNo(),
                variables
        );

        ticket.setProcessInstanceId(processInstance.getId());
        ticketRepository.save(ticket);

        log.info("工单 {} 工作流已启动，流程实例ID: {}", ticket.getTicketNo(), processInstance.getId());
        return processInstance.getId();
    }

    @Transactional
    public String startProcess(Ticket ticket, User assignee, WorkflowContext context) {
        Map<String, Object> variables = context.toMap();
        variables.put("creator", ticket.getCreator().getId());
        variables.put("assignee", assignee != null ? assignee.getId() : null);
        variables.put("assigned", assignee != null);
        variables.put("resolved", false);
        variables.put("confirmed", false);
        variables.put(WorkflowContext.KEY, context);

        WorkflowContext.setCurrent(context);
        try {
            ProcessInstance processInstance = runtimeService.startProcessInstanceByKey(
                    "ticketWorkflow",
                    ticket.getTicketNo(),
                    variables
            );

            ticket.setProcessInstanceId(processInstance.getId());
            context.setProcessInstanceId(processInstance.getId());
            ticketRepository.save(ticket);

            log.info("工单 {} 工作流已启动，流程实例ID: {}, 使用全局上下文", ticket.getTicketNo(), processInstance.getId());
            return processInstance.getId();
        } finally {
            WorkflowContext.clear();
        }
    }

    public Task getCurrentTask(String processInstanceId) {
        return taskService.createTaskQuery()
                .processInstanceId(processInstanceId)
                .singleResult();
    }

    @Transactional
    public void completeTask(String processInstanceId, Long userId, Map<String, Object> variables) {
        Task task = getCurrentTask(processInstanceId);
        if (task == null) {
            throw new BusinessException("未找到当前待办任务");
        }

        if (userId != null && !userId.toString().equals(task.getAssignee())) {
            throw new BusinessException("该任务不属于当前用户");
        }

        taskService.complete(task.getId(), variables);
        log.info("任务 {} 已完成，流程实例: {}", task.getId(), processInstanceId);
    }

    @Transactional
    public void completeTaskWithContext(String processInstanceId, Long userId, WorkflowContext context) {
        Task task = getCurrentTask(processInstanceId);
        if (task == null) {
            log.warn("未找到当前待办任务，流程实例: {}", processInstanceId);
            updateProcessVariables(processInstanceId, context);
            return;
        }

        if (userId != null && !userId.toString().equals(task.getAssignee())) {
            throw new BusinessException("该任务不属于当前用户");
        }

        Map<String, Object> variables = context.toMap();
        variables.put(WorkflowContext.KEY, context);

        WorkflowContext.setCurrent(context);
        try {
            taskService.complete(task.getId(), variables);
            log.info("任务 {} 已完成，流程实例: {}, 使用全局上下文", task.getId(), processInstanceId);
        } finally {
            WorkflowContext.clear();
        }
    }

    private void updateProcessVariables(String processInstanceId, WorkflowContext context) {
        Map<String, Object> variables = context.toMap();
        for (Map.Entry<String, Object> entry : variables.entrySet()) {
            runtimeService.setVariable(processInstanceId, entry.getKey(), entry.getValue());
        }
        runtimeService.setVariable(processInstanceId, WorkflowContext.KEY, context);
        log.debug("已更新流程变量，流程实例: {}", processInstanceId);
    }

    public WorkflowContext getWorkflowContext(String processInstanceId) {
        Object contextObj = runtimeService.getVariable(processInstanceId, WorkflowContext.KEY);
        if (contextObj instanceof WorkflowContext) {
            return (WorkflowContext) contextObj;
        }

        Map<String, Object> variables = runtimeService.getVariables(processInstanceId);
        return WorkflowContext.fromMap(variables);
    }

    @Transactional
    public void claimTask(String taskId, Long userId) {
        taskService.claim(taskId, userId.toString());
        log.info("任务 {} 已被用户 {} 签收", taskId, userId);
    }

    @Transactional
    public void transferTask(String taskId, Long fromUserId, Long toUserId) {
        Task task = taskService.createTaskQuery().taskId(taskId).singleResult();
        if (task == null) {
            throw new BusinessException("任务不存在");
        }
        if (!fromUserId.toString().equals(task.getAssignee())) {
            throw new BusinessException("只有任务处理人才能转办");
        }
        taskService.setAssignee(taskId, toUserId.toString());
        log.info("任务 {} 已从用户 {} 转办给用户 {}", taskId, fromUserId, toUserId);
    }

    public void setVariable(String processInstanceId, String key, Object value) {
        runtimeService.setVariable(processInstanceId, key, value);
    }

    public Object getVariable(String processInstanceId, String key) {
        return runtimeService.getVariable(processInstanceId, key);
    }

    @Transactional
    public void suspendProcess(String processInstanceId) {
        runtimeService.suspendProcessInstanceById(processInstanceId);
        log.info("流程实例 {} 已挂起", processInstanceId);
    }

    @Transactional
    public void activateProcess(String processInstanceId) {
        runtimeService.activateProcessInstanceById(processInstanceId);
        log.info("流程实例 {} 已激活", processInstanceId);
    }

    @Transactional
    public void deleteProcess(String processInstanceId, String reason) {
        runtimeService.deleteProcessInstance(processInstanceId, reason);
        log.info("流程实例 {} 已删除，原因: {}", processInstanceId, reason);
    }
}
