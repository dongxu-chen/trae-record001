package com.loganalytics.parser;

import com.loganalytics.model.NginxLogEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class NginxLogParser {
    private static final Logger LOG = LoggerFactory.getLogger(NginxLogParser.class);

    private static final Pattern NGINX_LOG_PATTERN = Pattern.compile(
            "^(\\S+)\\s+(\\S+)\\s+(\\S+)\\s+\\[([^\\]]+)\\]\\s+\"([^\"]*)\"\\s+(\\d+)\\s+(\\d+)\\s+\"([^\"]*)\"\\s+\"([^\"]*)\"\\s*\"?([^\"]*)?\"?$"
    );

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter
            .ofPattern("dd/MMM/yyyy:HH:mm:ss Z", Locale.ENGLISH);

    private static final Pattern REQUEST_PATTERN = Pattern.compile(
            "^(\\S+)\\s+(\\S+)\\s+(\\S+)$"
    );

    private static final Pattern EXTENDED_LOG_PATTERN = Pattern.compile(
            "^(\\S+)\\s+(\\S+)\\s+(\\S+)\\s+\\[([^\\]]+)\\]\\s+\"([^\"]*)\"\\s+(\\d+)\\s+(\\d+)\\s+\"([^\"]*)\"\\s+\"([^\"]*)\"\\s+(\\S+)\\s+(\\S+)\\s+\"([^\"]*)\"\\s*\"?([^\"]*)?\"?$"
    );

    public static NginxLogEvent parse(String logLine) {
        try {
            Matcher matcher = EXTENDED_LOG_PATTERN.matcher(logLine);
            if (matcher.matches()) {
                return parseExtendedFormat(matcher);
            }

            matcher = NGINX_LOG_PATTERN.matcher(logLine);
            if (matcher.matches()) {
                return parseStandardFormat(matcher);
            }

            LOG.warn("Failed to parse log line: {}", logLine);
            return null;
        } catch (Exception e) {
            LOG.error("Error parsing log line: {}", logLine, e);
            return null;
        }
    }

    private static NginxLogEvent parseStandardFormat(Matcher matcher) {
        NginxLogEvent.NginxLogEventBuilder builder = NginxLogEvent.builder();

        builder.remoteAddr(matcher.group(1));
        builder.remoteUser(matcher.group(3));
        builder.timestamp(parseTimestamp(matcher.group(4)));

        String request = matcher.group(5);
        builder.request(request);
        parseRequest(builder, request);

        builder.status(Integer.parseInt(matcher.group(6)));
        builder.bodyBytesSent(Long.parseLong(matcher.group(7)));
        builder.httpReferer(matcher.group(8));
        builder.httpUserAgent(matcher.group(9));

        return builder.build();
    }

    private static NginxLogEvent parseExtendedFormat(Matcher matcher) {
        NginxLogEvent.NginxLogEventBuilder builder = NginxLogEvent.builder();

        builder.remoteAddr(matcher.group(1));
        builder.remoteUser(matcher.group(3));
        builder.timestamp(parseTimestamp(matcher.group(4)));

        String request = matcher.group(5);
        builder.request(request);
        parseRequest(builder, request);

        builder.status(Integer.parseInt(matcher.group(6)));
        builder.bodyBytesSent(Long.parseLong(matcher.group(7)));
        builder.httpReferer(matcher.group(8));
        builder.httpUserAgent(matcher.group(9));

        try {
            builder.requestTime(Double.parseDouble(matcher.group(10)));
        } catch (NumberFormatException e) {
            builder.requestTime(0.0);
        }

        try {
            builder.upstreamResponseTime(parseUpstreamTime(matcher.group(11)));
        } catch (Exception e) {
            builder.upstreamResponseTime(0.0);
        }

        builder.upstreamStatus(matcher.group(12));
        builder.host(matcher.group(13));

        return builder.build();
    }

    private static void parseRequest(NginxLogEvent.NginxLogEventBuilder builder, String request) {
        if (request == null || request.isEmpty()) {
            return;
        }

        Matcher requestMatcher = REQUEST_PATTERN.matcher(request);
        if (requestMatcher.matches()) {
            builder.method(requestMatcher.group(1));
            String uri = requestMatcher.group(2);
            builder.uri(uri);
            builder.path(extractPath(uri));
        }
    }

    private static String extractPath(String uri) {
        if (uri == null) {
            return "/";
        }
        int queryIndex = uri.indexOf('?');
        return queryIndex > 0 ? uri.substring(0, queryIndex) : uri;
    }

    private static long parseTimestamp(String timestampStr) {
        try {
            LocalDateTime dateTime = LocalDateTime.parse(timestampStr, DATE_FORMATTER);
            return dateTime.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
        } catch (Exception e) {
            LOG.warn("Failed to parse timestamp: {}", timestampStr, e);
            return System.currentTimeMillis();
        }
    }

    private static double parseUpstreamTime(String timeStr) {
        if (timeStr == null || timeStr.equals("-")) {
            return 0.0;
        }
        try {
            return Double.parseDouble(timeStr);
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }
}
