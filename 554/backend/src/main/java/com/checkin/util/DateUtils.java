package com.checkin.util;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAdjusters;

public class DateUtils {

    private static final ZoneId UTC_ZONE = ZoneId.of("UTC");
    private static final ZoneId DEFAULT_ZONE = ZoneId.systemDefault();

    public static LocalDate getUtcToday() {
        return LocalDate.now(UTC_ZONE);
    }

    public static LocalDateTime getUtcNow() {
        return LocalDateTime.now(UTC_ZONE);
    }

    public static LocalDate toUtcDate(LocalDate localDate) {
        return localDate;
    }

    public static LocalDate getPeriodStartUtc(String periodType, LocalDate date) {
        LocalDate utcDate = date != null ? date : getUtcToday();
        switch (periodType) {
            case "DAILY":
                return utcDate;
            case "WEEKLY":
                return utcDate.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
            case "MONTHLY":
                return utcDate.with(TemporalAdjusters.firstDayOfMonth());
            default:
                return utcDate.with(TemporalAdjusters.firstDayOfMonth());
        }
    }

    public static LocalDate getPeriodEndUtc(String periodType, LocalDate date) {
        LocalDate utcDate = date != null ? date : getUtcToday();
        switch (periodType) {
            case "DAILY":
                return utcDate;
            case "WEEKLY":
                return utcDate.with(TemporalAdjusters.nextOrSame(DayOfWeek.SUNDAY));
            case "MONTHLY":
                return utcDate.with(TemporalAdjusters.lastDayOfMonth());
            default:
                return utcDate.with(TemporalAdjusters.lastDayOfMonth());
        }
    }

    public static String getPeriodUtc(String periodType, LocalDate date) {
        LocalDate utcDate = date != null ? date : getUtcToday();
        switch (periodType) {
            case "DAILY":
                return utcDate.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            case "WEEKLY":
                return utcDate.getYear() + "-W" + utcDate.get(java.time.temporal.WeekFields.ISO.weekOfWeekBasedYear());
            case "MONTHLY":
                return utcDate.format(DateTimeFormatter.ofPattern("yyyy-MM"));
            default:
                return utcDate.format(DateTimeFormatter.ofPattern("yyyy-MM"));
        }
    }

    public static int calculateDayIndexUtc(String periodType, LocalDate date, LocalDate startDate) {
        LocalDate utcDate = date != null ? date : getUtcToday();
        LocalDate utcStart = startDate != null ? startDate : getPeriodStartUtc(periodType, utcDate);
        
        switch (periodType) {
            case "DAILY":
                return Period.between(utcStart, utcDate).getDays() + 1;
            case "WEEKLY":
                return utcDate.getDayOfWeek().getValue();
            case "MONTHLY":
                return utcDate.getDayOfMonth();
            default:
                return utcDate.getDayOfMonth();
        }
    }

    public static boolean isSameDayUtc(LocalDate date1, LocalDate date2) {
        return date1.isEqual(date2);
    }

    public static long daysBetweenUtc(LocalDate start, LocalDate end) {
        return java.time.temporal.ChronoUnit.DAYS.between(start, end);
    }

    public static LocalDate getUtcYesterday() {
        return getUtcToday().minusDays(1);
    }

    public static LocalDate getUtcDaysAgo(int days) {
        return getUtcToday().minusDays(days);
    }

    public static boolean isWithinRecheckWindow(LocalDate checkinDate, int maxDays) {
        LocalDate today = getUtcToday();
        LocalDate earliestDate = today.minusDays(maxDays);
        return !checkinDate.isBefore(earliestDate) && checkinDate.isBefore(today);
    }

    public static boolean hasBreakInContinuous(LocalDate lastCheckinDate, LocalDate today) {
        if (lastCheckinDate == null) {
            return true;
        }
        long daysBetween = daysBetweenUtc(lastCheckinDate, today);
        return daysBetween > 1;
    }

    public static int calculateContinuousDaysUtc(LocalDate lastCheckinDate, int currentContinuous, LocalDate today) {
        if (lastCheckinDate == null) {
            return 1;
        }
        
        long daysSinceLastCheckin = daysBetweenUtc(lastCheckinDate, today);
        
        if (daysSinceLastCheckin == 1) {
            return currentContinuous + 1;
        } else if (daysSinceLastCheckin == 0) {
            return currentContinuous;
        } else {
            return 1;
        }
    }
}
