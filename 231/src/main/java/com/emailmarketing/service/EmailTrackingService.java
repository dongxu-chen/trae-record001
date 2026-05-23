package com.emailmarketing.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class EmailTrackingService {

    private static final Pattern LINK_PATTERN = Pattern.compile(
            "<a\\s+[^>]*href\\s*=\\s*['\"]([^'\"]+)['\"][^>]*>",
            Pattern.CASE_INSENSITIVE
    );

    private static final Pattern CATEGORY_PATTERN = Pattern.compile(
            "data-category=['\"]([^'\"]+)['\"]",
            Pattern.CASE_INSENSITIVE
    );

    @Value("${email.tracking.base-url}")
    private String baseUrl;

    public String injectTracking(String content, Long taskId, Long logId, String email) {
        String encodedEmail = encodeEmail(email);
        content = injectLinkTracking(content, taskId, logId, encodedEmail);
        content = injectOpenTracking(content, taskId, logId, encodedEmail, null);
        content = injectUnsubscribeLink(content, taskId, logId, encodedEmail);
        return content;
    }

    public String injectTracking(String content, Long taskId, Long logId, String email, String defaultCategory) {
        String encodedEmail = encodeEmail(email);
        content = injectLinkTracking(content, taskId, logId, encodedEmail);
        content = injectOpenTracking(content, taskId, logId, encodedEmail, defaultCategory);
        content = injectUnsubscribeLink(content, taskId, logId, encodedEmail);
        return content;
    }

    private String injectLinkTracking(String content, Long taskId, Long logId, String encodedEmail) {
        StringBuffer result = new StringBuffer();
        Matcher matcher = LINK_PATTERN.matcher(content);

        while (matcher.find()) {
            String originalHref = matcher.group(1);
            String fullMatch = matcher.group();
            if (isTrackableLink(originalHref)) {
                String category = extractCategory(fullMatch);
                String trackingUrl = buildTrackingUrl(taskId, logId, encodedEmail, originalHref, category);
                String replacement = fullMatch.replace(originalHref, trackingUrl);
                matcher.appendReplacement(result, Matcher.quoteReplacement(replacement));
            }
        }
        matcher.appendTail(result);
        return result.toString();
    }

    private String extractCategory(String anchorTag) {
        Matcher categoryMatcher = CATEGORY_PATTERN.matcher(anchorTag);
        if (categoryMatcher.find()) {
            return categoryMatcher.group(1);
        }
        return null;
    }

    private boolean isTrackableLink(String href) {
        if (href == null || href.isEmpty()) {
            return false;
        }
        String lower = href.toLowerCase();
        return lower.startsWith("http://") || lower.startsWith("https://");
    }

    private String buildTrackingUrl(Long taskId, Long logId, String encodedEmail, String originalUrl, String category) {
        try {
            String encodedUrl = URLEncoder.encode(originalUrl, StandardCharsets.UTF_8.name());
            StringBuilder sb = new StringBuilder();
            sb.append(baseUrl).append("/api/tracking/click?taskId=").append(taskId)
                    .append("&logId=").append(logId)
                    .append("&email=").append(encodedEmail)
                    .append("&url=").append(encodedUrl);
            if (category != null && !category.isEmpty()) {
                sb.append("&category=").append(URLEncoder.encode(category, StandardCharsets.UTF_8.name()));
            }
            return sb.toString();
        } catch (UnsupportedEncodingException e) {
            return originalUrl;
        }
    }

    private String injectOpenTracking(String content, Long taskId, Long logId, String encodedEmail, String category) {
        StringBuilder pixelUrl = new StringBuilder();
        pixelUrl.append(baseUrl).append("/api/tracking/open?taskId=").append(taskId)
                .append("&logId=").append(logId)
                .append("&email=").append(encodedEmail);
        if (category != null && !category.isEmpty()) {
            try {
                pixelUrl.append("&category=").append(URLEncoder.encode(category, StandardCharsets.UTF_8.name()));
            } catch (UnsupportedEncodingException ignored) {}
        }
        String trackingPixel = "<img src=\"" + pixelUrl + "\" style=\"display:none;width:1px;height:1px;\" alt=\"\" />";
        
        if (content.toLowerCase().contains("</body>")) {
            content = content.replaceAll("(?i)</body>", trackingPixel + "</body>");
        } else {
            content += trackingPixel;
        }
        return content;
    }

    private String injectUnsubscribeLink(String content, Long taskId, Long logId, String encodedEmail) {
        String unsubscribeUrl = baseUrl + "/api/tracking/unsubscribe?taskId=" + taskId + "&logId=" + logId + "&email=" + encodedEmail;
        String unsubscribeLink = "<div style=\"margin-top:30px;padding-top:20px;border-top:1px solid #eee;text-align:center;font-size:12px;color:#999;\">" +
                "<p>如果您不想再收到此类邮件，请<a href=\"" + unsubscribeUrl + "\" style=\"color:#999;text-decoration:underline;\">点击这里退订</a></p>" +
                "</div>";
        content += unsubscribeLink;
        return content;
    }

    private String encodeEmail(String email) {
        try {
            return URLEncoder.encode(email, StandardCharsets.UTF_8.name());
        } catch (UnsupportedEncodingException e) {
            return email.replace("@", "%40");
        }
    }
}
