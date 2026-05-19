package com.scheduler.raft;

import lombok.extern.slf4j.Slf4j;
import org.quartz.Scheduler;
import org.quartz.SchedulerException;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;

@Slf4j
@Component
public class SchedulerManager {

    @Resource
    private Scheduler scheduler;

    @Resource
    private RaftNode raftNode;

    private volatile boolean schedulerActive = false;

    @PostConstruct
    public void init() {
        raftNode.addStateChangeListener(this::handleStateChange);
        log.info("调度器管理器初始化完成");
    }

    private void handleStateChange(RaftNode.NodeState newState) {
        log.info("节点状态变更为: {}, 调度器当前状态: {}", newState, schedulerActive);

        if (newState == RaftNode.NodeState.LEADER) {
            activateScheduler();
        } else {
            deactivateScheduler();
        }
    }

    public synchronized void activateScheduler() {
        if (schedulerActive) {
            log.info("调度器已经处于激活状态");
            return;
        }

        try {
            if (!scheduler.isStarted()) {
                scheduler.start();
                schedulerActive = true;
                log.info("调度器已激活，开始执行任务调度");
            } else if (scheduler.isInStandbyMode()) {
                scheduler.resumeAll();
                schedulerActive = true;
                log.info("调度器已从待机模式恢复");
            }
        } catch (SchedulerException e) {
            log.error("激活调度器失败", e);
        }
    }

    public synchronized void deactivateScheduler() {
        if (!schedulerActive) {
            log.info("调度器已经处于非激活状态");
            return;
        }

        try {
            scheduler.pauseAll();
            schedulerActive = false;
            log.info("调度器已暂停，不再执行任务调度");
        } catch (SchedulerException e) {
            log.error("暂停调度器失败", e);
        }
    }

    public boolean isSchedulerActive() {
        return schedulerActive;
    }

    public String getSchedulerStatus() {
        try {
            if (scheduler.isShutdown()) {
                return "SHUTDOWN";
            }
            if (scheduler.isInStandbyMode()) {
                return "STANDBY";
            }
            if (scheduler.isStarted()) {
                return schedulerActive ? "ACTIVE" : "STARTED_PAUSED";
            }
            return "INITIALIZED";
        } catch (SchedulerException e) {
            return "ERROR";
        }
    }
}
