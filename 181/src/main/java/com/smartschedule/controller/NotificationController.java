package com.smartschedule.controller;

import com.smartschedule.dto.ApiResponse;
import com.smartschedule.entity.Employee;
import com.smartschedule.entity.Notification;
import com.smartschedule.service.EmployeeService;
import com.smartschedule.service.PushNotificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/notifications")
@CrossOrigin(origins = "*")
public class NotificationController {

    @Autowired
    private PushNotificationService pushNotificationService;

    @Autowired
    private EmployeeService employeeService;

    @GetMapping("/employee/{employeeId}")
    public ResponseEntity<ApiResponse<List<Notification>>> getEmployeeNotifications(
            @PathVariable Long employeeId) {
        return ResponseEntity.ok(ApiResponse.success(
                pushNotificationService.getEmployeeNotifications(employeeId)));
    }

    @GetMapping("/schedule/{scheduleId}")
    public ResponseEntity<ApiResponse<List<Notification>>> getScheduleNotifications(
            @PathVariable Long scheduleId) {
        return ResponseEntity.ok(ApiResponse.success(
                pushNotificationService.getScheduleNotifications(scheduleId)));
    }

    @PostMapping("/send-pending")
    public ResponseEntity<ApiResponse<Void>> sendPendingNotifications() {
        pushNotificationService.sendPendingNotifications();
        return ResponseEntity.ok(ApiResponse.success());
    }

    @PostMapping("/test/{employeeId}")
    public ResponseEntity<ApiResponse<Void>> sendTestNotification(
            @PathVariable Long employeeId,
            @RequestParam String title,
            @RequestParam String content) {
        Employee employee = employeeService.getEmployee(employeeId);
        pushNotificationService.sendTestNotification(employee, title, content);
        return ResponseEntity.ok(ApiResponse.success());
    }
}
