package com.smartschedule.service;

import com.smartschedule.entity.Employee;
import com.smartschedule.entity.Notification;
import com.smartschedule.entity.Schedule;
import com.smartschedule.entity.ShiftAssignment;
import com.smartschedule.repository.NotificationRepository;
import com.smartschedule.repository.ShiftAssignmentRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class PushNotificationService {

    private static final Logger logger = LoggerFactory.getLogger(PushNotificationService.class);

    @Autowired
    private NotificationRepository notificationRepository;

    @Autowired
    private ShiftAssignmentRepository assignmentRepository;

    @Autowired
    private PushService pushService;

    @Transactional
    public void createSchedulePublishedNotifications(Schedule schedule) {
        List<ShiftAssignment> assignments = assignmentRepository.findByScheduleId(schedule.getId());
        Map<Employee, List<ShiftAssignment>> employeeAssignments = assignments.stream()
                .filter(a -> a.getEmployee() != null)
                .collect(Collectors.groupingBy(ShiftAssignment::getEmployee));

        for (Map.Entry<Employee, List<ShiftAssignment>> entry : employeeAssignments.entrySet()) {
            Employee employee = entry.getKey();
            List<ShiftAssignment> empShifts = entry.getValue();

            String content = buildSchedulePublishedContent(employee, schedule, empShifts);

            Notification notification = new Notification();
            notification.setEmployee(employee);
            notification.setSchedule(schedule);
            notification.setTitle("新排班已发布");
            notification.setContent(content);
            notification.setType(Notification.NotificationType.SCHEDULE_PUBLISHED);
            notification.setChannel(Notification.NotificationChannel.APP_PUSH);

            notificationRepository.save(notification);
        }
    }

    private String buildSchedulePublishedContent(Employee employee, Schedule schedule, List<ShiftAssignment> assignments) {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("%s您好，您的排班已发布。\n", employee.getName()));
        sb.append(String.format("排班周期：%s 至 %s\n",
                schedule.getStartDate().format(DateTimeFormatter.ISO_LOCAL_DATE),
                schedule.getEndDate().format(DateTimeFormatter.ISO_LOCAL_DATE)));
        sb.append("您的班次安排：\n");

        assignments.stream()
                .sorted((a1, a2) -> a1.getShiftRequirement().getDate()
                        .compareTo(a2.getShiftRequirement().getDate()))
                .forEach(a -> {
                    sb.append(String.format("- %s %s (%s-%s)\n",
                            a.getShiftRequirement().getDate().format(DateTimeFormatter.ISO_LOCAL_DATE),
                            a.getShiftRequirement().getShiftType().getName(),
                            a.getShiftRequirement().getShiftType().getStartTime(),
                            a.getShiftRequirement().getShiftType().getEndTime()));
                });

        return sb.toString();
    }

    @Async
    public void sendPendingNotifications() {
        List<Notification> pendingNotifications = notificationRepository
                .findByStatus(Notification.NotificationStatus.PENDING);

        for (Notification notification : pendingNotifications) {
            try {
                boolean success = pushService.sendNotification(notification);
                if (success) {
                    notification.setStatus(Notification.NotificationStatus.SENT);
                    notification.setSentAt(LocalDateTime.now());
                } else {
                    notification.setStatus(Notification.NotificationStatus.FAILED);
                    notification.setErrorMessage("Push service returned failure");
                }
            } catch (Exception e) {
                logger.error("Failed to send notification: {}", notification.getId(), e);
                notification.setStatus(Notification.NotificationStatus.FAILED);
                notification.setErrorMessage(e.getMessage());
            }
            notificationRepository.save(notification);
        }
    }

    @Transactional
    public void createShiftChangeNotification(ShiftAssignment oldAssignment, ShiftAssignment newAssignment) {
        Employee employee = newAssignment.getEmployee();
        if (employee == null) return;

        StringBuilder content = new StringBuilder();
        content.append(String.format("%s您好，您的排班有变动。\n", employee.getName()));

        if (oldAssignment != null && oldAssignment.getEmployee() != null) {
            content.append(String.format("原班次：%s %s\n",
                    oldAssignment.getShiftRequirement().getDate(),
                    oldAssignment.getShiftRequirement().getShiftType().getName()));
        }

        content.append(String.format("新班次：%s %s (%s-%s)\n",
                newAssignment.getShiftRequirement().getDate(),
                newAssignment.getShiftRequirement().getShiftType().getName(),
                newAssignment.getShiftRequirement().getShiftType().getStartTime(),
                newAssignment.getShiftRequirement().getShiftType().getEndTime()));

        Notification notification = new Notification();
        notification.setEmployee(employee);
        notification.setSchedule(newAssignment.getSchedule());
        notification.setTitle("排班变动通知");
        notification.setContent(content.toString());
        notification.setType(Notification.NotificationType.SHIFT_CHANGED);
        notification.setChannel(Notification.NotificationChannel.APP_PUSH);

        notificationRepository.save(notification);
    }

    public List<Notification> getEmployeeNotifications(Long employeeId) {
        return notificationRepository.findByEmployeeId(employeeId);
    }

    public List<Notification> getScheduleNotifications(Long scheduleId) {
        return notificationRepository.findByScheduleId(scheduleId);
    }

    @Transactional
    public void sendTestNotification(Employee employee, String title, String content) {
        Notification notification = new Notification();
        notification.setEmployee(employee);
        notification.setTitle(title);
        notification.setContent(content);
        notification.setType(Notification.NotificationType.REMINDER);
        notification.setChannel(Notification.NotificationChannel.APP_PUSH);
        notificationRepository.save(notification);

        pushService.sendNotification(notification);
    }
}
