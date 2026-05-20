package com.smartschedule.repository;

import com.smartschedule.entity.Notification;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface NotificationRepository extends JpaRepository<Notification, Long> {
    List<Notification> findByEmployeeId(Long employeeId);
    List<Notification> findByScheduleId(Long scheduleId);
    List<Notification> findByStatus(Notification.NotificationStatus status);
    List<Notification> findByEmployeeIdAndStatus(Long employeeId, Notification.NotificationStatus status);
}
