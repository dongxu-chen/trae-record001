package com.checkin.service;

import com.checkin.entity.*;
import com.checkin.repository.*;
import com.checkin.util.DateUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.*;
import java.time.temporal.ChronoUnit;
import java.util.*;

@Service
public class ReminderService {

    @Autowired
    private CheckinReminderRepository reminderRepository;

    @Autowired
    private CheckinRecordRepository checkinRecordRepository;

    @Autowired
    private CheckinStatsRepository statsRepository;

    @Autowired
    private PushRecordRepository pushRecordRepository;

    @Autowired
    private UserRepository userRepository;

    public List<CheckinReminder> getUserReminders(Long userId) {
        return reminderRepository.findByUserId(userId);
    }

    @Transactional
    public CheckinReminder saveReminder(CheckinReminder reminder) {
        Optional<CheckinReminder> existing = reminderRepository
                .findByUserIdAndReminderType(reminder.getUserId(), reminder.getReminderType());
        
        if (existing.isPresent()) {
            CheckinReminder update = existing.get();
            update.setEnabled(reminder.getEnabled());
            update.setReminderTime(reminder.getReminderTime());
            update.setPushChannel(reminder.getPushChannel());
            update.setAdvanceMinutes(reminder.getAdvanceMinutes());
            return reminderRepository.save(update);
        }
        
        return reminderRepository.save(reminder);
    }

    @Transactional
    public void deleteReminder(Long id) {
        reminderRepository.deleteById(id);
    }

    @Scheduled(cron = "0 * * * * *")
    @Transactional
    public void checkAndSendReminders() {
        LocalDateTime now = DateUtils.getUtcNow();
        LocalDate today = DateUtils.getUtcToday();
        
        List<CheckinReminder> reminders = reminderRepository.findByEnabledTrue();
        
        for (CheckinReminder reminder : reminders) {
            if (shouldSendReminder(reminder, now, today)) {
                sendReminder(reminder, today);
            }
        }
    }

    private boolean shouldSendReminder(CheckinReminder reminder, LocalDateTime now, LocalDate today) {
        if (!reminder.getEnabled()) {
            return false;
        }

        if (checkinRecordRepository.existsByUserIdAndCheckinDateAndPeriodType(
                reminder.getUserId(), today, "DAILY")) {
            return false;
        }

        if (reminder.getLastSent() && reminder.getLastSendTime() != null) {
            if (reminder.getLastSendTime().toLocalDate().isEqual(today)) {
                return false;
            }
        }

        String reminderTimeStr = reminder.getReminderTime();
        if (reminderTimeStr == null || reminderTimeStr.length() < 5) {
            reminderTimeStr = "20:00";
        }

        int hour = Integer.parseInt(reminderTimeStr.substring(0, 2));
        int minute = Integer.parseInt(reminderTimeStr.substring(3, 5));
        
        LocalTime reminderTime = LocalTime.of(hour, minute);
        LocalTime nowTime = now.toLocalTime();
        
        long minutesUntilReminder = ChronoUnit.MINUTES.between(nowTime, reminderTime);
        int advanceMinutes = reminder.getAdvanceMinutes() != null ? reminder.getAdvanceMinutes() : 0;
        
        return minutesUntilReminder >= 0 && minutesUntilReminder <= 5 + advanceMinutes / 60;
    }

    @Transactional
    public PushRecord sendReminder(CheckinReminder reminder, LocalDate today) {
        User user = userRepository.findById(reminder.getUserId()).orElse(null);
        if (user == null) {
            return null;
        }

        String period = DateUtils.getPeriodUtc("DAILY", today);
        CheckinStats stats = statsRepository
                .findByUserIdAndPeriodTypeAndPeriod(reminder.getUserId(), "DAILY", period)
                .orElse(null);

        int continuousDays = stats != null ? stats.getContinuousDays() : 0;
        
        String title;
        String content;
        
        if ("CONTINUOUS_WARNING".equals(reminder.getReminderType())) {
            title = "⚠️ 连续签到临期提醒";
            if (continuousDays >= 6) {
                content = String.format(
                    "您已连续签到%d天，今日签到即将结束！\n错过将重置连续签到天数，赶紧签到吧！",
                    continuousDays);
            } else {
                content = String.format(
                    "您已连续签到%d天，今日还未签到！\n保持连续签到可获得更多奖励~",
                    continuousDays);
            }
        } else if ("DAILY".equals(reminder.getReminderType())) {
            title = "📅 每日签到提醒";
            if (continuousDays > 0) {
                content = String.format(
                    "今天还没签到哦~\n当前连续签到%d天，继续保持！",
                    continuousDays);
            } else {
                content = "今日签到还未完成，快来签到领取奖励吧！";
            }
        } else if ("TREASURE_WARNING".equals(reminder.getReminderType())) {
            title = "💎 宝箱即将达成提醒";
            int remainingDays = 7 - (continuousDays % 7);
            if (remainingDays <= 2) {
                content = String.format(
                    "还差%d天即可解锁新宝箱！\n今日签到后距离目标更近一步~",
                    remainingDays);
            } else {
                content = String.format(
                    "累计签到%d天，继续加油！\n坚持签到解锁更多宝箱奖励~",
                    continuousDays);
            }
        } else {
            title = "签到提醒";
            content = "今日签到还未完成，快来签到吧！";
        }

        PushRecord pushRecord = new PushRecord();
        pushRecord.setUserId(reminder.getUserId());
        pushRecord.setPushType(reminder.getReminderType());
        pushRecord.setPushChannel(reminder.getPushChannel() != null ? reminder.getPushChannel() : "APP");
        pushRecord.setTitle(title);
        pushRecord.setContent(content);
        pushRecord.setSuccess(true);
        pushRecord.setSendTime(DateUtils.getUtcNow());
        pushRecordRepository.save(pushRecord);

        reminder.setLastSent(true);
        reminder.setLastSendTime(DateUtils.getUtcNow());
        reminderRepository.save(reminder);

        return pushRecord;
    }

    public List<PushRecord> getPushHistory(Long userId, int limit) {
        List<PushRecord> records = pushRecordRepository.findByUserIdOrderByCreateTimeDesc(userId);
        return records.stream().limit(limit).collect(java.util.stream.Collectors.toList());
    }

    @Transactional
    public PushRecord sendCustomReminder(Long userId, String type, String title, String content) {
        PushRecord pushRecord = new PushRecord();
        pushRecord.setUserId(userId);
        pushRecord.setPushType(type);
        pushRecord.setPushChannel("SYSTEM");
        pushRecord.setTitle(title);
        pushRecord.setContent(content);
        pushRecord.setSuccess(true);
        pushRecord.setSendTime(DateUtils.getUtcNow());
        return pushRecordRepository.save(pushRecord);
    }

    public Map<String, Object> getReminderStatus(Long userId) {
        Map<String, Object> result = new HashMap<>();
        LocalDate today = DateUtils.getUtcToday();
        String period = DateUtils.getPeriodUtc("DAILY", today);
        
        CheckinStats stats = statsRepository
                .findByUserIdAndPeriodTypeAndPeriod(userId, "DAILY", period)
                .orElse(null);
        
        int continuousDays = stats != null ? stats.getContinuousDays() : 0;
        boolean todayChecked = checkinRecordRepository
                .existsByUserIdAndCheckinDateAndPeriodType(userId, today, "DAILY");
        
        result.put("todayChecked", todayChecked);
        result.put("continuousDays", continuousDays);
        result.put("continuousBrokenRisk", !todayChecked && continuousDays > 0);
        result.put("nextTreasureDays", 7 - (continuousDays % 7));
        result.put("nearTreasure", (7 - (continuousDays % 7)) <= 2);
        
        List<CheckinReminder> reminders = reminderRepository.findByUserId(userId);
        Map<String, Boolean> reminderEnabled = new HashMap<>();
        for (CheckinReminder r : reminders) {
            reminderEnabled.put(r.getReminderType(), r.getEnabled());
        }
        result.put("reminders", reminderEnabled);
        
        return result;
    }
}
