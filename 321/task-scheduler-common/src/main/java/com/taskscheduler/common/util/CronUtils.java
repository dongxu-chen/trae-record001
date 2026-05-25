package com.taskscheduler.common.util;

import cn.hutool.core.date.DateUtil;
import org.quartz.CronExpression;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class CronUtils {

    public static boolean isValid(String cronExpression) {
        return CronExpression.isValidExpression(cronExpression);
    }

    public static Date getNextValidTimeAfter(String cronExpression, Date date) {
        try {
            CronExpression cron = new CronExpression(cronExpression);
            return cron.getNextValidTimeAfter(date);
        } catch (ParseException e) {
            throw new RuntimeException("Invalid cron expression: " + cronExpression, e);
        }
    }

    public static List<String> getNextExecutionTimes(String cronExpression, int count) {
        List<String> times = new ArrayList<>();
        try {
            CronExpression cron = new CronExpression(cronExpression);
            Date date = new Date();
            for (int i = 0; i < count; i++) {
                date = cron.getNextValidTimeAfter(date);
                if (date == null) {
                    break;
                }
                times.add(DateUtil.formatDateTime(date));
            }
        } catch (ParseException e) {
            throw new RuntimeException("Invalid cron expression: " + cronExpression, e);
        }
        return times;
    }
}
