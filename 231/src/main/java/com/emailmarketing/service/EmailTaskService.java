package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.config.RabbitMQConfig;
import com.emailmarketing.dto.EmailSendMessage;
import com.emailmarketing.entity.EmailSendLog;
import com.emailmarketing.entity.EmailTask;
import com.emailmarketing.entity.EmailTemplate;
import com.emailmarketing.entity.Recipient;
import com.emailmarketing.mapper.EmailTaskMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class EmailTaskService extends ServiceImpl<EmailTaskMapper, EmailTask> {

    private static final String UNSUBSCRIBE_CACHE_PREFIX = "email:unsubscribed:";

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private EmailTemplateService templateService;

    @Autowired
    private RecipientService recipientService;

    @Autowired
    private EmailSendLogService sendLogService;

    @Autowired
    private EmailTrackingService trackingService;

    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    @Value("${email.tracking.base-url}")
    private String baseUrl;

    public Page<EmailTask> listTasks(int page, int size, String name, Integer status) {
        Page<EmailTask> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<EmailTask> wrapper = new LambdaQueryWrapper<>();
        if (name != null && !name.isEmpty()) {
            wrapper.like(EmailTask::getName, name);
        }
        if (status != null) {
            wrapper.eq(EmailTask::getStatus, status);
        }
        wrapper.orderByDesc(EmailTask::getCreatedAt);
        return page(pageParam, wrapper);
    }

    @Transactional(rollbackFor = Exception.class)
    public boolean createTask(EmailTask task) {
        EmailTemplate template = templateService.getTemplateById(task.getTemplateId());
        if (template == null || template.getStatus() != 1) {
            throw new RuntimeException("模板不存在或未启用");
        }

        List<Recipient> recipients = recipientService.getActiveRecipientsByGroup(task.getGroupId());
        if (recipients.isEmpty()) {
            throw new RuntimeException("收件人分组为空");
        }

        task.setTotalCount(recipients.size());
        task.setSentCount(0);
        task.setSuccessCount(0);
        task.setFailCount(0);
        task.setUnsubscribeCount(0);
        task.setStatus(0);
        boolean saved = save(task);

        if (saved && task.getTaskType() == 1) {
            startTask(task.getId());
        }

        return saved;
    }

    @Transactional(rollbackFor = Exception.class)
    public void startTask(Long taskId) {
        EmailTask task = getById(taskId);
        if (task == null || task.getStatus() != 0) {
            return;
        }

        EmailTemplate template = templateService.getTemplateById(task.getTemplateId());
        List<Recipient> recipients = recipientService.getActiveRecipientsByGroup(task.getGroupId());

        task.setStatus(1);
        updateById(task);

        for (Recipient recipient : recipients) {
            if (isUnsubscribed(recipient.getEmail())) {
                continue;
            }

            EmailSendLog sendLog = new EmailSendLog();
            sendLog.setTaskId(taskId);
            sendLog.setRecipientId(recipient.getId());
            sendLog.setEmail(recipient.getEmail());
            sendLog.setSendStatus(0);
            sendLog.setOpened(0);
            sendLog.setClicked(0);
            sendLog.setUnsubscribed(0);
            sendLog.setCreatedAt(LocalDateTime.now());
            sendLogService.save(sendLog);

            String content = trackingService.injectTracking(template.getContent(), taskId, sendLog.getId(), recipient.getEmail());

            EmailSendMessage message = new EmailSendMessage(
                    taskId,
                    sendLog.getId(),
                    recipient.getId(),
                    recipient.getEmail(),
                    template.getSubject(),
                    content
            );

            rabbitTemplate.convertAndSend(RabbitMQConfig.EMAIL_EXCHANGE, RabbitMQConfig.EMAIL_ROUTING_KEY, message);
        }

        task.setSentCount(recipients.size());
        updateById(task);
    }

    public void handleRecipientUnsubscribe(Long taskId, Long recipientId, String email) {
        markAsUnsubscribed(email);
        LambdaUpdateWrapper<EmailTask> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(EmailTask::getId, taskId);
        wrapper.setSql("unsubscribe_count = unsubscribe_count + 1");
        update(wrapper);
        log.info("Recipient unsubscribed: taskId={}, recipientId={}, email={}", taskId, recipientId, email);
    }

    private void markAsUnsubscribed(String email) {
        String key = UNSUBSCRIBE_CACHE_PREFIX + email.toLowerCase();
        redisTemplate.opsForValue().set(key, "1", 7, TimeUnit.DAYS);
    }

    public boolean isUnsubscribed(String email) {
        String key = UNSUBSCRIBE_CACHE_PREFIX + email.toLowerCase();
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }

    @Scheduled(fixedDelay = 60000)
    public void checkScheduledTasks() {
        LocalDateTime now = LocalDateTime.now();
        LambdaQueryWrapper<EmailTask> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(EmailTask::getStatus, 0);
        wrapper.eq(EmailTask::getTaskType, 2);
        wrapper.le(EmailTask::getScheduleTime, now);
        
        List<EmailTask> tasks = list(wrapper);
        for (EmailTask task : tasks) {
            startTask(task.getId());
        }
    }

    public void incrementSuccessCount(Long taskId) {
        LambdaUpdateWrapper<EmailTask> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(EmailTask::getId, taskId);
        wrapper.setSql("success_count = success_count + 1");
        update(wrapper);
        checkTaskComplete(taskId);
    }

    public void incrementFailCount(Long taskId) {
        LambdaUpdateWrapper<EmailTask> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(EmailTask::getId, taskId);
        wrapper.setSql("fail_count = fail_count + 1");
        update(wrapper);
        checkTaskComplete(taskId);
    }

    private void checkTaskComplete(Long taskId) {
        EmailTask task = getById(taskId);
        if (task != null && task.getSuccessCount() + task.getFailCount() >= task.getSentCount()) {
            task.setStatus(2);
            updateById(task);
        }
    }

    public boolean cancelTask(Long taskId) {
        EmailTask task = getById(taskId);
        if (task == null || task.getStatus() != 0) {
            return false;
        }
        task.setStatus(3);
        return updateById(task);
    }
}
