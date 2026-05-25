package com.tracking.common.util;

import com.alibaba.fastjson2.JSONObject;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class UserAgentUtil {

    private static final Pattern PATTERN_OS = Pattern.compile("\\(([^)]+)\\)");
    private static final Pattern PATTERN_BROWSER = Pattern.compile("(Chrome|Safari|Firefox|Edge|Opera|MSIE|Trident)/([\\d.]+)");
    private static final Pattern PATTERN_DEVICE = Pattern.compile("(iPhone|iPad|Android|Windows Phone|Macintosh|Windows|Linux)");

    public static JSONObject parse(String userAgent) {
        JSONObject result = new JSONObject();
        if (userAgent == null || userAgent.isEmpty()) {
            return result;
        }

        result.put("raw", userAgent);

        String os = extractOS(userAgent);
        result.put("os", os);
        result.put("osVersion", extractOSVersion(userAgent, os));

        String browser = extractBrowser(userAgent);
        result.put("browser", browser);
        result.put("browserVersion", extractBrowserVersion(userAgent, browser));

        result.put("device", extractDevice(userAgent));
        result.put("isMobile", isMobile(userAgent));
        result.put("isBot", isBot(userAgent));

        return result;
    }

    private static String extractOS(String ua) {
        if (ua.contains("Windows NT")) {
            return "Windows";
        } else if (ua.contains("Mac OS X")) {
            return "Mac OS";
        } else if (ua.contains("Linux")) {
            return "Linux";
        } else if (ua.contains("Android")) {
            return "Android";
        } else if (ua.contains("iPhone") || ua.contains("iPad")) {
            return "iOS";
        } else if (ua.contains("Windows Phone")) {
            return "Windows Phone";
        }
        return "Unknown";
    }

    private static String extractOSVersion(String ua, String os) {
        try {
            if ("Windows".equals(os)) {
                Pattern p = Pattern.compile("Windows NT ([\\d.]+)");
                Matcher m = p.matcher(ua);
                if (m.find()) {
                    return m.group(1);
                }
            } else if ("Android".equals(os)) {
                Pattern p = Pattern.compile("Android ([\\d.]+)");
                Matcher m = p.matcher(ua);
                if (m.find()) {
                    return m.group(1);
                }
            } else if ("iOS".equals(os)) {
                Pattern p = Pattern.compile("OS ([\\d_]+) like Mac OS");
                Matcher m = p.matcher(ua);
                if (m.find()) {
                    return m.group(1).replace("_", ".");
                }
            }
        } catch (Exception e) {
            return null;
        }
        return null;
    }

    private static String extractBrowser(String ua) {
        Matcher m = PATTERN_BROWSER.matcher(ua);
        if (m.find()) {
            String browser = m.group(1);
            if ("Trident".equals(browser)) {
                return "IE";
            }
            return browser;
        }
        return "Unknown";
    }

    private static String extractBrowserVersion(String ua, String browser) {
        try {
            if ("IE".equals(browser)) {
                Pattern p = Pattern.compile("rv:([\\d.]+)");
                Matcher m = p.matcher(ua);
                if (m.find()) {
                    return m.group(1);
                }
            } else {
                Pattern p = Pattern.compile(browser + "/([\\d.]+)");
                Matcher m = p.matcher(ua);
                if (m.find()) {
                    return m.group(1);
                }
            }
        } catch (Exception e) {
            return null;
        }
        return null;
    }

    private static String extractDevice(String ua) {
        Matcher m = PATTERN_DEVICE.matcher(ua);
        if (m.find()) {
            return m.group(1);
        }
        return "Unknown";
    }

    public static boolean isMobile(String ua) {
        return ua != null && (ua.contains("Mobile") || ua.contains("Android")
                || ua.contains("iPhone") || ua.contains("iPad") || ua.contains("Windows Phone"));
    }

    public static boolean isBot(String ua) {
        if (ua == null) {
            return false;
        }
        String lower = ua.toLowerCase();
        return lower.contains("bot") || lower.contains("spider") || lower.contains("crawler")
                || lower.contains("slurp") || lower.contains("curl") || lower.contains("wget");
    }
}
