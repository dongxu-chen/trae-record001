package com.drill.platform.scheduler;

import com.drill.platform.model.*;
import com.drill.platform.service.DrillService;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.support.CronTrigger;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;

@Component
public class DrillScheduler {

    private final TaskScheduler taskScheduler;
    private final DrillService drillService;
    
    private final Map<String, ScheduledDrill> scheduledDrills = new ConcurrentHashMap<>();
    private final Map<String, ScheduledFuture<?>> scheduledTasks = new ConcurrentHashMap<>();

    public DrillScheduler(TaskScheduler taskScheduler, DrillService drillService) {
        this.taskScheduler = taskScheduler;
        this.drillService = drillService;
    }

    @PostConstruct
    public void init() {
        loadScheduledDrills();
    }

    @PreDestroy
    public void destroy() {
        scheduledTasks.values().forEach(task -> task.cancel(false));
        scheduledTasks.clear();
    }

    private void loadScheduledDrills() {
    }

    public ScheduledDrill createScheduledDrill(ScheduledDrill drill) {
        drill.setId(UUID.randomUUID().toString());
        drill.setCreateTime(new Date());
        drill.setUpdateTime(new Date());
        drill.setExecutionCount(0);
        drill.setSuccessCount(0);
        drill.setConsecutiveFailures(0);
        drill.setStatus(drill.getEnabled() ? ScheduledDrill.Status.ACTIVE.name() : ScheduledDrill.Status.PAUSED.name());
        
        if (drill.getEnabled() == null) {
            drill.setEnabled(true);
        }
        
        calculateNextExecutionTime(drill);
        scheduledDrills.put(drill.getId(), drill);
        
        if (drill.getEnabled()) {
            scheduleTask(drill);
        }
        
        return drill;
    }

    public ScheduledDrill updateScheduledDrill(String id, ScheduledDrill updated) {
        ScheduledDrill existing = scheduledDrills.get(id);
        if (existing == null) {
            return null;
        }
        
        cancelTask(id);
        
        existing.setName(updated.getName());
        existing.setDescription(updated.getDescription());
        existing.setCronExpression(updated.getCronExpression());
        existing.setFrequency(updated.getFrequency());
        existing.setTrafficProfile(updated.getTrafficProfile());
        existing.setStrategyId(updated.getStrategyId());
        existing.setNotificationEmails(updated.getNotificationEmails());
        existing.setEnabled(updated.getEnabled());
        existing.setAutoPauseOnFailure(updated.getAutoPauseOnFailure());
        existing.setUpdateTime(new Date());
        
        if (updated.getEnabled()) {
            existing.setStatus(ScheduledDrill.Status.ACTIVE.name());
            calculateNextExecutionTime(existing);
            scheduleTask(existing);
        } else {
            existing.setStatus(ScheduledDrill.Status.PAUSED.name());
        }
        
        return existing;
    }

    public boolean deleteScheduledDrill(String id) {
        cancelTask(id);
        return scheduledDrills.remove(id) != null;
    }

    public ScheduledDrill getScheduledDrill(String id) {
        return scheduledDrills.get(id);
    }

    public List<ScheduledDrill> listScheduledDrills() {
        return new ArrayList<>(scheduledDrills.values());
    }

    public ScheduledDrill toggleScheduledDrill(String id, boolean enabled) {
        ScheduledDrill drill = scheduledDrills.get(id);
        if (drill == null) {
            return null;
        }
        
        if (enabled) {
            drill.setEnabled(true);
            drill.setStatus(ScheduledDrill.Status.ACTIVE.name());
            calculateNextExecutionTime(drill);
            scheduleTask(drill);
        } else {
            drill.setEnabled(false);
            drill.setStatus(ScheduledDrill.Status.PAUSED.name());
            cancelTask(id);
        }
        
        drill.setUpdateTime(new Date());
        return drill;
    }

    private void scheduleTask(ScheduledDrill drill) {
        if (drill.getCronExpression() == null) {
            generateCronExpression(drill);
        }
        
        CronTrigger trigger = new CronTrigger(drill.getCronExpression());
        ScheduledFuture<?> future = taskScheduler.schedule(() -> executeDrill(drill), trigger);
        scheduledTasks.put(drill.getId(), future);
    }

    private void cancelTask(String id) {
        ScheduledFuture<?> future = scheduledTasks.remove(id);
        if (future != null) {
            future.cancel(false);
        }
    }

    private void executeDrill(ScheduledDrill drill) {
        try {
            DrillTask task = new DrillTask();
            task.setName("定时演练 - " + drill.getName());
            task.setDescription(drill.getDescription());
            task.setStrategyId(drill.getStrategyId());
            task.setTrafficProfile(drill.getTrafficProfile());
            
            drillService.createTask(task);
            drillService.startTask(task.getId(), "simulator");
            
            drill.setLastExecutionTime(new Date());
            drill.setExecutionCount(drill.getExecutionCount() + 1);
            drill.setSuccessCount(drill.getSuccessCount() + 1);
            drill.setConsecutiveFailures(0);
            
        } catch (Exception e) {
            drill.setConsecutiveFailures(drill.getConsecutiveFailures() + 1);
            
            if (drill.getAutoPauseOnFailure() != null && drill.getAutoPauseOnFailure() 
                    && drill.getConsecutiveFailures() >= 3) {
                drill.setEnabled(false);
                drill.setStatus(ScheduledDrill.Status.ERROR.name());
                cancelTask(drill.getId());
            }
        }
        
        calculateNextExecutionTime(drill);
        drill.setUpdateTime(new Date());
    }

    private void generateCronExpression(ScheduledDrill drill) {
        String frequency = drill.getFrequency();
        if (frequency == null) {
            frequency = ScheduledDrill.Frequency.DAILY.name();
        }
        
        Random random = new Random();
        int minute = random.nextInt(60);
        int hour = random.nextInt(8) + 1;
        
        switch (ScheduledDrill.Frequency.valueOf(frequency)) {
            case HOURLY:
                drill.setCronExpression(String.format("0 %d * * * ?", minute));
                break;
            case DAILY:
                drill.setCronExpression(String.format("0 %d %d * * ?", minute, hour));
                break;
            case WEEKLY:
                int dayOfWeek = random.nextInt(5) + 1;
                drill.setCronExpression(String.format("0 %d %d ? * %d", minute, hour, dayOfWeek));
                break;
            case MONTHLY:
                int dayOfMonth = random.nextInt(28) + 1;
                drill.setCronExpression(String.format("0 %d %d %d * ?", minute, hour, dayOfMonth));
                break;
            default:
                drill.setCronExpression(String.format("0 %d %d * * ?", minute, hour));
        }
    }

    private void calculateNextExecutionTime(ScheduledDrill drill) {
        Calendar cal = Calendar.getInstance();
        cal.setTime(new Date());
        
        String frequency = drill.getFrequency();
        if (frequency == null) {
            frequency = ScheduledDrill.Frequency.DAILY.name();
        }
        
        switch (ScheduledDrill.Frequency.valueOf(frequency)) {
            case HOURLY:
                cal.add(Calendar.HOUR, 1);
                break;
            case DAILY:
                cal.add(Calendar.DAY_OF_MONTH, 1);
                break;
            case WEEKLY:
                cal.add(Calendar.WEEK_OF_MONTH, 1);
                break;
            case MONTHLY:
                cal.add(Calendar.MONTH, 1);
                break;
            default:
                cal.add(Calendar.DAY_OF_MONTH, 1);
        }
        
        drill.setNextExecutionTime(cal.getTime());
    }

    public Map<String, Object> getSchedulerStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalScheduled", scheduledDrills.size());
        stats.put("activeCount", scheduledDrills.values().stream()
                .filter(d -> ScheduledDrill.Status.ACTIVE.name().equals(d.getStatus())).count());
        stats.put("pausedCount", scheduledDrills.values().stream()
                .filter(d -> ScheduledDrill.Status.PAUSED.name().equals(d.getStatus())).count());
        stats.put("totalExecutions", scheduledDrills.values().stream()
                .mapToInt(ScheduledDrill::getExecutionCount).sum());
        stats.put("successRate", scheduledDrills.values().stream()
                .mapToInt(ScheduledDrill::getSuccessCount).sum() * 100.0 /
                Math.max(1, scheduledDrills.values().stream()
                        .mapToInt(ScheduledDrill::getExecutionCount).sum()));
        return stats;
    }
}
