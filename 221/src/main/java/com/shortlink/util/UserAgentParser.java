package com.shortlink.util;

import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class UserAgentParser {

    private static final Pattern MOBILE_PATTERN = Pattern.compile("(android|iphone|ipod|ipad|mobile|phone)", Pattern.CASE_INSENSITIVE);
    private static final Pattern TABLET_PATTERN = Pattern.compile("(ipad|tablet)", Pattern.CASE_INSENSITIVE);
    private static final Pattern DESKTOP_PATTERN = Pattern.compile("(windows|macintosh|linux)", Pattern.CASE_INSENSITIVE);

    private static final Pattern CHROME_PATTERN = Pattern.compile("Chrome/(\\d+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern FIREFOX_PATTERN = Pattern.compile("Firefox/(\\d+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern SAFARI_PATTERN = Pattern.compile("Version/(\\d+).*Safari", Pattern.CASE_INSENSITIVE);
    private static final Pattern EDGE_PATTERN = Pattern.compile("Edg/(\\d+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern IE_PATTERN = Pattern.compile("MSIE (\\d+)|Trident/.*rv:(\\d+)", Pattern.CASE_INSENSITIVE);

    private static final Pattern WINDOWS_PATTERN = Pattern.compile("Windows NT ([\\d.]+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern MAC_PATTERN = Pattern.compile("Mac OS X ([\\d_]+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern ANDROID_PATTERN = Pattern.compile("Android ([\\d.]+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern IOS_PATTERN = Pattern.compile("OS (\\d+_\\d+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern LINUX_PATTERN = Pattern.compile("Linux", Pattern.CASE_INSENSITIVE);

    public Map<String, String> parse(String userAgent) {
        Map<String, String> result = new HashMap<>();

        if (userAgent == null || userAgent.isBlank()) {
            result.put("deviceType", "Unknown");
            result.put("browser", "Unknown");
            result.put("os", "Unknown");
            return result;
        }

        result.put("deviceType", parseDeviceType(userAgent));
        result.put("browser", parseBrowser(userAgent));
        result.put("os", parseOS(userAgent));

        return result;
    }

    private String parseDeviceType(String userAgent) {
        Matcher tabletMatcher = TABLET_PATTERN.matcher(userAgent);
        if (tabletMatcher.find()) {
            return "Tablet";
        }

        Matcher mobileMatcher = MOBILE_PATTERN.matcher(userAgent);
        if (mobileMatcher.find()) {
            return "Mobile";
        }

        Matcher desktopMatcher = DESKTOP_PATTERN.matcher(userAgent);
        if (desktopMatcher.find()) {
            return "Desktop";
        }

        return "Other";
    }

    private String parseBrowser(String userAgent) {
        Matcher edgeMatcher = EDGE_PATTERN.matcher(userAgent);
        if (edgeMatcher.find()) {
            return "Edge " + edgeMatcher.group(1);
        }

        Matcher ieMatcher = IE_PATTERN.matcher(userAgent);
        if (ieMatcher.find()) {
            String version = ieMatcher.group(1) != null ? ieMatcher.group(1) : ieMatcher.group(2);
            return "IE " + version;
        }

        Matcher chromeMatcher = CHROME_PATTERN.matcher(userAgent);
        if (chromeMatcher.find() && !userAgent.contains("Edg")) {
            return "Chrome " + chromeMatcher.group(1);
        }

        Matcher firefoxMatcher = FIREFOX_PATTERN.matcher(userAgent);
        if (firefoxMatcher.find()) {
            return "Firefox " + firefoxMatcher.group(1);
        }

        Matcher safariMatcher = SAFARI_PATTERN.matcher(userAgent);
        if (safariMatcher.find() && !userAgent.contains("Chrome")) {
            return "Safari " + safariMatcher.group(1);
        }

        return "Unknown";
    }

    private String parseOS(String userAgent) {
        Matcher windowsMatcher = WINDOWS_PATTERN.matcher(userAgent);
        if (windowsMatcher.find()) {
            return "Windows " + windowsMatcher.group(1);
        }

        Matcher macMatcher = MAC_PATTERN.matcher(userAgent);
        if (macMatcher.find()) {
            return "macOS " + macMatcher.group(1).replace("_", ".");
        }

        Matcher androidMatcher = ANDROID_PATTERN.matcher(userAgent);
        if (androidMatcher.find()) {
            return "Android " + androidMatcher.group(1);
        }

        Matcher iosMatcher = IOS_PATTERN.matcher(userAgent);
        if (iosMatcher.find() && (userAgent.contains("iPhone") || userAgent.contains("iPad"))) {
            return "iOS " + iosMatcher.group(1).replace("_", ".");
        }

        Matcher linuxMatcher = LINUX_PATTERN.matcher(userAgent);
        if (linuxMatcher.find()) {
            return "Linux";
        }

        return "Unknown";
    }
}
