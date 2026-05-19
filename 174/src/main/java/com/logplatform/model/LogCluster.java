package com.logplatform.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LogCluster {

    private String clusterId;

    private String representativeMessage;

    private List<LogEntry> logs;

    private int size;

    private double similarityScore;

    private String category;

    public static LogCluster create(LogEntry initialLog) {
        return LogCluster.builder()
                .clusterId("cluster_" + System.currentTimeMillis() + "_" + Math.abs(initialLog.hashCode()))
                .representativeMessage(initialLog.getMessage())
                .logs(new ArrayList<>(List.of(initialLog)))
                .size(1)
                .similarityScore(1.0)
                .build();
    }

    public boolean addLogIfSimilar(LogEntry log, double threshold) {
        double similarity = calculateSimilarity(representativeMessage, log.getMessage());
        if (similarity >= threshold) {
            logs.add(log);
            size++;
            similarityScore = calculateAverageSimilarity();
            if (log.getMessage().length() < representativeMessage.length()) {
                representativeMessage = log.getMessage();
            }
            return true;
        }
        return false;
    }

    public static double calculateSimilarity(String s1, String s2) {
        if (s1 == null || s2 == null) return 0;
        if (s1.equals(s2)) return 1.0;

        String[] tokens1 = tokenize(s1);
        String[] tokens2 = tokenize(s2);

        int matches = 0;
        for (String t1 : tokens1) {
            for (String t2 : tokens2) {
                if (t1.equalsIgnoreCase(t2)) {
                    matches++;
                    break;
                }
            }
        }

        double jaccard = (double) matches / (tokens1.length + tokens2.length - matches);

        int editDistance = levenshteinDistance(s1, s2);
        double lengthRatio = 1.0 - (double) Math.abs(s1.length() - s2.length()) / Math.max(s1.length(), s2.length());
        double editSimilarity = 1.0 - (double) editDistance / Math.max(s1.length(), s2.length());

        return (jaccard * 0.4 + editSimilarity * 0.4 + lengthRatio * 0.2);
    }

    private static String[] tokenize(String s) {
        return s.toLowerCase()
                .replaceAll("[^a-zA-Z0-9\\s]", " ")
                .split("\\s+");
    }

    private static int levenshteinDistance(String s1, String s2) {
        int[][] dp = new int[s1.length() + 1][s2.length() + 1];

        for (int i = 0; i <= s1.length(); i++) dp[i][0] = i;
        for (int j = 0; j <= s2.length(); j++) dp[0][j] = j;

        for (int i = 1; i <= s1.length(); i++) {
            for (int j = 1; j <= s2.length(); j++) {
                int cost = s1.charAt(i - 1) == s2.charAt(j - 1) ? 0 : 1;
                dp[i][j] = Math.min(Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1), dp[i - 1][j - 1] + cost);
            }
        }

        return dp[s1.length()][s2.length()];
    }

    private double calculateAverageSimilarity() {
        if (logs.size() < 2) return 1.0;
        double total = 0;
        int count = 0;
        for (int i = 0; i < logs.size(); i++) {
            for (int j = i + 1; j < logs.size(); j++) {
                total += calculateSimilarity(logs.get(i).getMessage(), logs.get(j).getMessage());
                count++;
            }
        }
        return count > 0 ? total / count : 1.0;
    }
}
