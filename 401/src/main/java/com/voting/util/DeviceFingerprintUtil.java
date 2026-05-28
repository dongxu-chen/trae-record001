package com.voting.util;

import org.apache.commons.codec.digest.DigestUtils;
import org.apache.commons.lang3.StringUtils;

import javax.servlet.http.HttpServletRequest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class DeviceFingerprintUtil {

    private static final String[] STABLE_HEADERS = {
            "User-Agent",
            "Accept-Language",
            "Accept",
            "DNT",
            "Sec-CH-UA",
            "Sec-CH-UA-Platform",
            "Sec-CH-UA-Mobile",
            "Connection"
    };

    private static final String[] SEMI_STABLE_HEADERS = {
            "Accept-Encoding",
            "Sec-CH-UA-Platform-Version",
            "Sec-CH-UA-Arch",
            "Sec-CH-UA-Bitness",
            "Sec-CH-UA-Model",
            "Sec-CH-UA-Full-Version-List"
    };

    public static String generateFingerprint(HttpServletRequest request) {
        List<String> featureHashes = new ArrayList<>();

        featureHashes.add(hashFeature("stable", generateStableFeatures(request)));

        featureHashes.add(hashFeature("semi", generateSemiStableFeatures(request)));

        featureHashes.add(hashFeature("network", generateNetworkFeatures(request)));

        featureHashes.sort(Comparator.naturalOrder());

        String combined = String.join("|", featureHashes);
        return DigestUtils.sha256Hex(combined);
    }

    private static String generateStableFeatures(HttpServletRequest request) {
        StringBuilder sb = new StringBuilder();
        for (String header : STABLE_HEADERS) {
            String value = normalizeHeader(getHeader(request, header));
            sb.append(header).append("=").append(value).append("|");
        }
        return sb.toString();
    }

    private static String generateSemiStableFeatures(HttpServletRequest request) {
        StringBuilder sb = new StringBuilder();
        for (String header : SEMI_STABLE_HEADERS) {
            String value = normalizeHeader(getHeader(request, header));
            if (StringUtils.isNotEmpty(value)) {
                sb.append(header).append("=").append(value).append("|");
            }
        }
        return sb.toString();
    }

    private static String generateNetworkFeatures(HttpServletRequest request) {
        String ip = getClientIp(request);
        String normalizedIp = normalizeIpForFingerprint(ip);

        StringBuilder sb = new StringBuilder();
        sb.append("ip_prefix=").append(normalizedIp).append("|");
        return sb.toString();
    }

    private static String normalizeHeader(String value) {
        if (value == null) {
            return "";
        }
        value = value.trim().toLowerCase();
        value = value.replaceAll("\\s+", " ");
        value = value.replaceAll("[\\d.]{5,}", "");
        return value;
    }

    private static String normalizeIpForFingerprint(String ip) {
        if (ip == null || ip.isEmpty()) {
            return "";
        }

        if (isIPv6(ip)) {
            return getIPv6Prefix(ip, 64);
        } else {
            String[] parts = ip.split("\\.");
            if (parts.length >= 3) {
                return parts[0] + "." + parts[1] + "." + parts[2];
            }
            return ip;
        }
    }

    private static String hashFeature(String category, String content) {
        if (StringUtils.isEmpty(content)) {
            return category + ":empty";
        }
        return category + ":" + DigestUtils.sha256Hex(content).substring(0, 16);
    }

    public static String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.length() == 0 || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.length() == 0 || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.length() == 0 || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_CLIENT_IP");
        }
        if (ip == null || ip.length() == 0 || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        }
        if (ip == null || ip.length() == 0 || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }

        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }

        return ip;
    }

    public static String getIpPrefixForLimit(String ip) {
        if (ip == null || ip.isEmpty()) {
            return "";
        }

        if (isIPv6(ip)) {
            return getIPv6Prefix(ip, 64);
        } else {
            return ip;
        }
    }

    private static boolean isIPv6(String ip) {
        return ip != null && ip.contains(":");
    }

    private static String getIPv6Prefix(String ip, int prefixLength) {
        try {
            if (ip.startsWith("[") && ip.endsWith("]")) {
                ip = ip.substring(1, ip.length() - 1);
            }

            int percentIndex = ip.indexOf('%');
            if (percentIndex > 0) {
                ip = ip.substring(0, percentIndex);
            }

            String[] parts = ip.split("::", -1);
            List<String> fullParts = new ArrayList<>();

            if (parts.length == 2) {
                String[] leftParts = parts[0].isEmpty() ? new String[0] : parts[0].split(":");
                String[] rightParts = parts[1].isEmpty() ? new String[0] : parts[1].split(":");
                int missing = 8 - leftParts.length - rightParts.length;

                for (String part : leftParts) {
                    fullParts.add(part.isEmpty() ? "0" : part);
                }
                for (int i = 0; i < missing; i++) {
                    fullParts.add("0");
                }
                for (String part : rightParts) {
                    fullParts.add(part.isEmpty() ? "0" : part);
                }
            } else {
                String[] splitParts = ip.split(":");
                for (String part : splitParts) {
                    fullParts.add(part.isEmpty() ? "0" : part);
                }
            }

            while (fullParts.size() < 8) {
                fullParts.add("0");
            }

            int groupsToKeep = prefixLength / 16;
            StringBuilder prefixBuilder = new StringBuilder();
            for (int i = 0; i < groupsToKeep && i < fullParts.size(); i++) {
                if (i > 0) {
                    prefixBuilder.append(":");
                }
                prefixBuilder.append(fullParts.get(i));
            }

            if (prefixLength % 16 != 0 && groupsToKeep < fullParts.size()) {
                int bitsInPartialGroup = prefixLength % 16;
                int mask = 0xFFFF << (16 - bitsInPartialGroup);
                int partialGroupValue = Integer.parseInt(fullParts.get(groupsToKeep), 16);
                int maskedValue = partialGroupValue & mask;
                prefixBuilder.append(":").append(Integer.toHexString(maskedValue));
            }

            return prefixBuilder.toString();
        } catch (Exception e) {
            return ip;
        }
    }

    private static String getHeader(HttpServletRequest request, String headerName) {
        String header = request.getHeader(headerName);
        return header != null ? header : "";
    }
}
