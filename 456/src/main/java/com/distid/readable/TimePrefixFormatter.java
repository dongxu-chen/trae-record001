package com.distid.readable;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

public class TimePrefixFormatter {

    private static final DateTimeFormatter COMPACT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");
    private static final DateTimeFormatter DATE_ONLY = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final DateTimeFormatter HOUR_MINUTE = DateTimeFormatter.ofPattern("yyyyMMddHHmm");

    public static String format(long epochMillis) {
        return COMPACT.format(Instant.ofEpochMilli(epochMillis).atZone(ZoneId.of("UTC")));
    }

    public static String formatDateOnly(long epochMillis) {
        return DATE_ONLY.format(Instant.ofEpochMilli(epochMillis).atZone(ZoneId.of("UTC")));
    }

    public static String formatHourMinute(long epochMillis) {
        return HOUR_MINUTE.format(Instant.ofEpochMilli(epochMillis).atZone(ZoneId.of("UTC")));
    }

    public static long extractTimestampFromTimePrefix(String timePrefix) {
        try {
            if (timePrefix.length() == 14) {
                return Instant.from(COMPACT.parse(timePrefix)).toEpochMilli();
            } else if (timePrefix.length() == 12) {
                return Instant.from(HOUR_MINUTE.parse(timePrefix)).toEpochMilli();
            } else if (timePrefix.length() == 8) {
                return Instant.from(DATE_ONLY.parse(timePrefix)).toEpochMilli();
            }
        } catch (Exception ignored) {
        }
        return -1;
    }
}
