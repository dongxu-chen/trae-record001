package com.meeting.booking.controller;

import com.meeting.booking.common.Result;
import com.meeting.booking.entity.Notification;
import com.meeting.booking.service.NotificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/notifications")
public class NotificationController {

    @Autowired
    private NotificationService notificationService;

    @GetMapping("/{id}")
    public Result<Notification> getById(@PathVariable Long id) {
        return Result.success(notificationService.getById(id));
    }

    @GetMapping("/user/{userId}")
    public Result<List<Notification>> getByUserId(
            @PathVariable Long userId,
            @RequestParam(required = false) Integer isRead) {
        return Result.success(notificationService.getByUserId(userId, isRead));
    }

    @GetMapping("/user/{userId}/unread-count")
    public Result<Integer> countUnread(@PathVariable Long userId) {
        return Result.success(notificationService.countUnread(userId));
    }

    @PostMapping("/{id}/read")
    public Result<Boolean> markAsRead(@PathVariable Long id) {
        return Result.success(notificationService.markAsRead(id));
    }

    @PostMapping("/user/{userId}/read-all")
    public Result<Boolean> markAllAsRead(@PathVariable Long userId) {
        return Result.success(notificationService.markAllAsRead(userId));
    }
}
