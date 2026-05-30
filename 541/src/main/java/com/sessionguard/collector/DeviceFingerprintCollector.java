package com.sessionguard.collector;

import com.sessionguard.model.DeviceFingerprint;
import jakarta.servlet.http.HttpServletRequest;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;

@Component
public class DeviceFingerprintCollector {

    public DeviceFingerprint collect(HttpServletRequest request) {
        String userAgent = request.getHeader("User-Agent");

        String platform = request.getHeader("Sec-CH-UA-Platform");
        String browserInfo = request.getHeader("Sec-CH-UA");
        String mobile = request.getHeader("Sec-CH-UA-Mobile");
        String architecture = request.getHeader("Sec-CH-UA-Arch");

        ParsedUserAgent parsed = parseUserAgent(StringUtils.defaultString(userAgent, ""));

        Map<String, String> clientAttributes = collectClientAttributes(request);

        DeviceFingerprint fingerprint = DeviceFingerprint.builder()
                .userAgent(userAgent)
                .platform(StringUtils.defaultString(platform, parsed.platform))
                .browser(parsed.browser)
                .browserVersion(parsed.browserVersion)
                .os(parsed.os)
                .osVersion(parsed.osVersion)
                .screenResolution(request.getHeader("Sec-CH-UA-Viewport-Width") != null
                        ? request.getHeader("Sec-CH-UA-Viewport-Width") : "UNKNOWN")
                .colorDepth(request.getHeader("Sec-CH-UA-Color-Scheme") != null
                        ? request.getHeader("Sec-CH-UA-Color-Scheme") : "UNKNOWN")
                .timezone(request.getHeader("Sec-CH-UA-Timezone") != null
                        ? request.getHeader("Sec-CH-UA-Timezone") : "UNKNOWN")
                .language(request.getLocale() != null ? request.getLocale().toString() : "UNKNOWN")
                .javaEnabled(false)
                .cookiesEnabled(true)
                .canvasHash(extractAttributeMap(clientAttributes, "canvas"))
                .webglHash(extractAttributeMap(clientAttributes, "webgl"))
                .audioHash(extractAttributeMap(clientAttributes, "audio"))
                .fontList(extractAttributeMap(clientAttributes, "font"))
                .build();

        fingerprint.setFingerprintHash(computeFingerprintHash(fingerprint));
        return fingerprint;
    }

    private Map<String, String> collectClientAttributes(HttpServletRequest request) {
        Map<String, String> attributes = new HashMap<>();
        String fpHeader = request.getHeader("X-Device-Fingerprint");
        if (StringUtils.isNotBlank(fpHeader)) {
            String[] parts = fpHeader.split(";");
            for (String part : parts) {
                String[] kv = part.split("=", 2);
                if (kv.length == 2) {
                    attributes.put(kv[0].trim(), kv[1].trim());
                }
            }
        }
        return attributes;
    }

    private Map<String, String> extractAttributeMap(Map<String, String> source, String prefix) {
        Map<String, String> result = new HashMap<>();
        source.forEach((key, value) -> {
            if (key.startsWith(prefix + "_")) {
                result.put(key, value);
            }
        });
        return result;
    }

    private String computeFingerprintHash(DeviceFingerprint fp) {
        StringBuilder sb = new StringBuilder();
        sb.append(StringUtils.defaultString(fp.getUserAgent(), ""));
        sb.append(StringUtils.defaultString(fp.getPlatform(), ""));
        sb.append(StringUtils.defaultString(fp.getBrowser(), ""));
        sb.append(StringUtils.defaultString(fp.getOs(), ""));
        sb.append(StringUtils.defaultString(fp.getScreenResolution(), ""));
        sb.append(StringUtils.defaultString(fp.getTimezone(), ""));
        sb.append(StringUtils.defaultString(fp.getLanguage(), ""));

        if (fp.getCanvasHash() != null) {
            fp.getCanvasHash().values().stream().sorted().forEach(sb::append);
        }
        if (fp.getWebglHash() != null) {
            fp.getWebglHash().values().stream().sorted().forEach(sb::append);
        }

        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(sb.toString().getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            return String.valueOf(sb.toString().hashCode());
        }
    }

    private ParsedUserAgent parseUserAgent(String ua) {
        ParsedUserAgent result = new ParsedUserAgent();

        if (ua.contains("Windows")) {
            result.os = "Windows";
            result.platform = "Windows";
            result.osVersion = extractVersion(ua, "Windows NT ");
        } else if (ua.contains("Mac OS X")) {
            result.os = "macOS";
            result.platform = "macOS";
            result.osVersion = extractVersion(ua, "Mac OS X ");
        } else if (ua.contains("Linux")) {
            result.os = "Linux";
            result.platform = "Linux";
            result.osVersion = "";
        } else if (ua.contains("Android")) {
            result.os = "Android";
            result.platform = "Android";
            result.osVersion = extractVersion(ua, "Android ");
        } else if (ua.contains("iPhone") || ua.contains("iPad")) {
            result.os = "iOS";
            result.platform = "iOS";
            result.osVersion = extractVersion(ua, "OS ");
        }

        if (ua.contains("Chrome/") && !ua.contains("Edg/")) {
            result.browser = "Chrome";
            result.browserVersion = extractVersion(ua, "Chrome/");
        } else if (ua.contains("Firefox/")) {
            result.browser = "Firefox";
            result.browserVersion = extractVersion(ua, "Firefox/");
        } else if (ua.contains("Safari/") && !ua.contains("Chrome")) {
            result.browser = "Safari";
            result.browserVersion = extractVersion(ua, "Version/");
        } else if (ua.contains("Edg/")) {
            result.browser = "Edge";
            result.browserVersion = extractVersion(ua, "Edg/");
        }

        return result;
    }

    private String extractVersion(String source, String prefix) {
        int idx = source.indexOf(prefix);
        if (idx < 0) return "";
        String sub = source.substring(idx + prefix.length());
        StringBuilder version = new StringBuilder();
        for (char c : sub.toCharArray()) {
            if (Character.isDigit(c) || c == '.') {
                version.append(c);
            } else {
                break;
            }
        }
        return version.toString();
    }

    private static class ParsedUserAgent {
        String platform = "Unknown";
        String browser = "Unknown";
        String browserVersion = "";
        String os = "Unknown";
        String osVersion = "";
    }
}
