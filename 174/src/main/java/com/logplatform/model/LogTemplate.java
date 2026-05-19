package com.logplatform.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LogTemplate {

    private String templateId;

    private String templatePattern;

    private String regexPattern;

    private String category;

    private long occurrenceCount;

    private long lastOccurrenceTime;

    private long firstOccurrenceTime;

    private List<String> sampleLogs;

    private double severityScore;

    private List<String> affectedServices;

    private Pattern compiledPattern;

    public boolean matches(String message) {
        if (compiledPattern == null) {
            compiledPattern = Pattern.compile(regexPattern);
        }
        return compiledPattern.matcher(message).find();
    }

    public static LogTemplate createFromMessage(String message) {
        String template = extractTemplate(message);
        String regex = convertToRegex(template);

        return LogTemplate.builder()
                .templateId(generateId(template))
                .templatePattern(template)
                .regexPattern(regex)
                .occurrenceCount(1)
                .firstOccurrenceTime(System.currentTimeMillis())
                .lastOccurrenceTime(System.currentTimeMillis())
                .sampleLogs(new ArrayList<>(List.of(message)))
                .severityScore(calculateSeverity(message))
                .affectedServices(new ArrayList<>())
                .build();
    }

    private static String extractTemplate(String message) {
        String template = message;

        template = template.replaceAll("\\b\\d{4}-\\d{2}-\\d{2}[T ]\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{3})?\\b", "<TIMESTAMP>");
        template = template.replaceAll("\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b", "<IP>");
        template = template.replaceAll("\\b[0-9a-fA-F-]{32,36}\\b", "<UUID>");
        template = template.replaceAll("\\b\\d+\\b", "<NUM>");
        template = template.replaceAll("\"[^\"]*\"", "<STRING>");
        template = template.replaceAll("'[^']*'", "<STRING>");

        return template;
    }

    private static String convertToRegex(String template) {
        String regex = template;
        regex = regex.replace("<TIMESTAMP>", "\\\\d{4}-\\\\d{2}-\\\\d{2}[T ]\\\\d{2}:\\\\d{2}:\\\\d{2}(?:\\\\.\\\\d{3})?");
        regex = regex.replace("<IP>", "\\\\d{1,3}\\\\.\\\\d{1,3}\\\\.\\\\d{1,3}\\\\.\\\\d{1,3}");
        regex = regex.replace("<UUID>", "[0-9a-fA-F-]{32,36}");
        regex = regex.replace("<NUM>", "\\\\d+");
        regex = regex.replace("<STRING>", "\"[^\"]*\"|'[^']*'");
        regex = regex.replace("?", "\\?");
        regex = regex.replace(".", "\\.");
        regex = regex.replace("*", "\\*");
        return regex;
    }

    private static String generateId(String template) {
        return "tpl_" + Math.abs(template.hashCode());
    }

    private static double calculateSeverity(String message) {
        double score = 0.0;
        String lower = message.toLowerCase();

        if (lower.contains("fatal") || lower.contains("critical")) score += 10;
        if (lower.contains("error") || lower.contains("exception")) score += 7;
        if (lower.contains("warn") || lower.contains("warning")) score += 4;
        if (lower.contains("timeout")) score += 6;
        if (lower.contains("fail") || lower.contains("failed")) score += 5;
        if (lower.contains("null") || lower.contains("npe")) score += 6;
        if (lower.contains("connection")) score += 3;
        if (lower.contains("database") || lower.contains("db")) score += 4;

        return Math.min(score, 10);
    }

    public void addSample(String message) {
        if (sampleLogs.size() < 10) {
            sampleLogs.add(message);
        }
    }

    public void incrementCount() {
        this.occurrenceCount++;
        this.lastOccurrenceTime = System.currentTimeMillis();
    }
}
