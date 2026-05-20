package com.pushplatform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.Executor;

@Service
public class ScheduledPushService {

    private static final Logger logger = LoggerFactory.getLogger(ScheduledPushService.class);

    @Resource
    private PushTaskService pushTaskService;

    @Resource(name = "pushBusinessExecutor")
    private Executor pushBusinessExecutor;

    @Scheduled(fixedDelay = 60000)
    public void processScheduledTasks() {
        try {
            LambdaQueryWrapper<com.pushplatform.entity.PushTask> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(com.pushplatform.entity.PushTask::getStatus, 0)
                    .isNotNull(com.pushplatform.entity.PushTask::getScheduleTime)
                    .le(com.pushplatform.entity.PushTask::getScheduleTime, LocalDateTime.now());

            List<com.pushplatform.entity.PushTask> tasks = pushTaskService.list(wrapper);
            
            if (tasks.isEmpty()) {
                return;
            }

            logger.info("Found {} scheduled push tasks to process", tasks.size());

            for (com.pushplatform.entity.PushTask task : tasks) {
                pushBusinessExecutor.execute(() -> processTask(task));
            }
        } catch (Exception e) {
            logger.error("Process scheduled tasks error", e);
        }
    }

    private void processTask(com.pushplatform.entity.PushTask task) {
        try {
            logger.info("Processing scheduled push task: {}", task.getTaskNo());
            
            pushTaskService.updateStatus(task.getId(), 0);

        } catch (Exception e) {
            logger.error("Process scheduled task error, taskNo: {}", task.getTaskNo(), e);
        }
    }

    public boolean cancelScheduledTask(Long taskId) {
        try {
            com.pushplatform.entity.PushTask task = pushTaskService.getById(taskId);
            if (task == null) {
                return false;
            }
            if (task.getStatus() != 0) {
                logger.warn("Task already processed, cannot cancel: {}", task.getTaskNo());
                return false;
            }
            
            task.setStatus(3);
            task.setUpdateTime(LocalDateTime.now());
            pushTaskService.updateById(task);
            
            logger.info("Cancelled scheduled task: {}", task.getTaskNo());
            return true;
        } catch (Exception e) {
            logger.error("Cancel scheduled task error, taskId: {}", taskId, e);
            return false;
        }
    }

    public List<com.pushplatform.entity.PushTask> getPendingScheduledTasks() {
        LambdaQueryWrapper<com.pushplatform.entity.PushTask> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(com.pushplatform.entity.PushTask::getStatus, 0)
                .isNotNull(com.pushplatform.entity.PushTask::getScheduleTime)
                .orderByAsc(com.pushplatform.entity.PushTask::getScheduleTime);
        return pushTaskService.list(wrapper);
    }
}
