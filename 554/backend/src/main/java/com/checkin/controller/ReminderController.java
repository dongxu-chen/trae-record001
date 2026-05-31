package com.checkin.controller;

import com.checkin.common.Result;
import com.checkin.entity.CheckinReminder;
import com.checkin.entity.PushRecord;
import com.checkin.service.ReminderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/reminder")
public class ReminderController {

    @Autowired
    private ReminderService reminderService;

    @GetMapping("/user/{userId}")
    public Result<List<CheckinReminder>> getUserReminders(@PathVariable Long userId) {
        try {
            List<CheckinReminder> reminders = reminderService.getUserReminders(userId);
            return Result.success(reminders);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping
    public Result<CheckinReminder> saveReminder(@RequestBody CheckinReminder reminder) {
        try {
            CheckinReminder saved = reminderService.saveReminder(reminder);
            return Result.success(saved);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteReminder(@PathVariable Long id) {
        try {
            reminderService.deleteReminder(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/send")
    public Result<PushRecord> sendCustomReminder(@RequestBody Map<String, Object> params) {
        try {
            Long userId = Long.valueOf(params.get("userId").toString());
            String type = (String) params.get("type");
            String title = (String) params.get("title");
            String content = (String) params.get("content");
            
            PushRecord record = reminderService.sendCustomReminder(userId, type, title, content);
            return Result.success(record);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/status/{userId}")
    public Result<Map<String, Object>> getReminderStatus(@PathVariable Long userId) {
        try {
            Map<String, Object> status = reminderService.getReminderStatus(userId);
            return Result.success(status);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/history/{userId}")
    public Result<List<PushRecord>> getPushHistory(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "20") int limit) {
        try {
            List<PushRecord> history = reminderService.getPushHistory(userId, limit);
            return Result.success(history);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/test/{userId}")
    public Result<PushRecord> testReminder(
            @PathVariable Long userId,
            @RequestParam String reminderType,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        try {
            if (date == null) {
                date = LocalDate.now();
            }
            
            CheckinReminder reminder = new CheckinReminder();
            reminder.setUserId(userId);
            reminder.setReminderType(reminderType);
            reminder.setEnabled(true);
            reminder.setPushChannel("TEST");
            
            PushRecord record = reminderService.sendReminder(reminder, date);
            return Result.success(record);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/types")
    public Result<List<Map<String, Object>>> getReminderTypes() {
        List<Map<String, Object>> types = List.of(
            Map.of("type", "DAILY", "name", "每日签到提醒", "description", "每天提醒用户签到"),
            Map.of("type", "CONTINUOUS_WARNING", "name", "连续签到临期提醒", "description", "连续签到即将中断时提醒"),
            Map.of("type", "TREASURE_WARNING", "name", "宝箱达成提醒", "description", "即将达成宝箱条件时提醒")
        );
        return Result.success(types);
    }

    @GetMapping("/channels")
    public Result<List<Map<String, Object>>> getPushChannels() {
        List<Map<String, Object>> channels = List.of(
            Map.of("channel", "APP", "name", "应用内推送"),
            Map.of("channel", "SMS", "name", "短信提醒"),
            Map.of("channel", "EMAIL", "name", "邮件提醒"),
            Map.of("channel", "WECHAT", "name", "微信推送")
        );
        return Result.success(channels);
    }
}
