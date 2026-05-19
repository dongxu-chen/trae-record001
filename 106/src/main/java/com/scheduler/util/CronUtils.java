package com.scheduler.util;

import org.quartz.CronExpression;

import java.text.ParseException;

public class CronUtils {

    public static boolean isValid(String cronExpression) {
        return CronExpression.isValidExpression(cronExpression);
    }

    public static String validate(String cronExpression) {
        if (cronExpression == null || cronExpression.trim().isEmpty()) {
            return "Cron表达式不能为空";
        }
        try {
            new CronExpression(cronExpression);
            return null;
        } catch (ParseException e) {
            return "Cron表达式格式错误: " + e.getMessage();
        }
    }

}
