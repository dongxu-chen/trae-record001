package com.tracking.common.util;

import java.util.regex.Pattern;

public class IPUtil {

    private static final Pattern IPV4_PATTERN = Pattern.compile(
            "^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$");

    private static final Pattern IPV6_PATTERN = Pattern.compile(
            "^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$");

    public static boolean isValidIP(String ip) {
        if (ip == null || ip.isEmpty()) {
            return false;
        }
        return IPV4_PATTERN.matcher(ip).matches() || IPV6_PATTERN.matcher(ip).matches();
    }

    public static String extractIP(String ip) {
        if (ip == null) {
            return null;
        }
        ip = ip.trim();
        if (ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return isValidIP(ip) ? ip : null;
    }

    public static boolean isInternalIP(String ip) {
        if (ip == null) {
            return false;
        }
        if (ip.startsWith("10.")) {
            return true;
        }
        if (ip.startsWith("172.")) {
            int second = Integer.parseInt(ip.split("\\.")[1]);
            return second >= 16 && second <= 31;
        }
        if (ip.startsWith("192.168.")) {
            return true;
        }
        return "127.0.0.1".equals(ip) || "localhost".equalsIgnoreCase(ip);
    }

    public static String maskIP(String ip) {
        if (ip == null) {
            return null;
        }
        if (isValidIP(ip)) {
            String[] parts = ip.split("\\.");
            if (parts.length == 4) {
                return parts[0] + "." + parts[1] + "." + parts[2] + ".0";
            }
        }
        return ip;
    }
}
