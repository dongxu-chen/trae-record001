package com.schemaregistry.util;

public class StringSimilarity {

    public static double calculateLevenshteinSimilarity(String s1, String s2) {
        if (s1 == null || s2 == null) {
            return 0.0;
        }
        if (s1.equals(s2)) {
            return 1.0;
        }

        String longer = s1;
        String shorter = s2;
        if (s1.length() < s2.length()) {
            longer = s2;
            shorter = s1;
        }

        int longerLength = longer.length();
        if (longerLength == 0) {
            return 1.0;
        }

        int distance = levenshteinDistance(longer, shorter);
        return (longerLength - distance) / (double) longerLength;
    }

    public static int levenshteinDistance(String s1, String s2) {
        int[] prev = new int[s2.length() + 1];
        int[] curr = new int[s2.length() + 1];

        for (int j = 0; j <= s2.length(); j++) {
            prev[j] = j;
        }

        for (int i = 1; i <= s1.length(); i++) {
            curr[0] = i;
            for (int j = 1; j <= s2.length(); j++) {
                int cost = (s1.charAt(i - 1) == s2.charAt(j - 1)) ? 0 : 1;
                curr[j] = Math.min(Math.min(curr[j - 1] + 1, prev[j] + 1), prev[j - 1] + cost);
            }
            int[] temp = prev;
            prev = curr;
            curr = temp;
        }

        return prev[s2.length()];
    }

    public static double calculateJaccardSimilarity(String s1, String s2) {
        if (s1 == null || s2 == null) {
            return 0.0;
        }
        if (s1.equals(s2)) {
            return 1.0;
        }

        java.util.Set<Character> set1 = new java.util.HashSet<>();
        java.util.Set<Character> set2 = new java.util.HashSet<>();

        for (char c : s1.toCharArray()) {
            set1.add(c);
        }
        for (char c : s2.toCharArray()) {
            set2.add(c);
        }

        java.util.Set<Character> intersection = new java.util.HashSet<>(set1);
        intersection.retainAll(set2);

        java.util.Set<Character> union = new java.util.HashSet<>(set1);
        union.addAll(set2);

        if (union.isEmpty()) {
            return 0.0;
        }

        return (double) intersection.size() / union.size();
    }

    public static double calculateCombinedSimilarity(String s1, String s2) {
        String normalized1 = normalizeFieldName(s1);
        String normalized2 = normalizeFieldName(s2);

        double levenshtein = calculateLevenshteinSimilarity(normalized1, normalized2);
        double jaccard = calculateJaccardSimilarity(normalized1, normalized2);

        return (levenshtein * 0.7) + (jaccard * 0.3);
    }

    public static String normalizeFieldName(String name) {
        if (name == null) {
            return "";
        }
        return name.toLowerCase()
                .replaceAll("[_\\-\\s]", "")
                .replaceAll("\\d+$", "");
    }

    public static boolean isLikelyRename(String oldName, String newName, double threshold) {
        if (oldName == null || newName == null) {
            return false;
        }
        if (oldName.equals(newName)) {
            return false;
        }

        double similarity = calculateCombinedSimilarity(oldName, newName);

        String normalizedOld = normalizeFieldName(oldName);
        String normalizedNew = normalizeFieldName(newName);

        boolean containsSubstring = normalizedOld.contains(normalizedNew) || normalizedNew.contains(normalizedOld);
        boolean startsOrEnds = normalizedNew.startsWith(normalizedOld.substring(0, Math.min(3, normalizedOld.length()))) ||
                               normalizedNew.endsWith(normalizedOld.substring(Math.max(0, normalizedOld.length() - 3)));

        return similarity >= threshold || (containsSubstring && similarity >= threshold * 0.8) || (startsOrEnds && similarity >= threshold * 0.7);
    }

    public static boolean isLikelyRename(String oldName, String newName) {
        return isLikelyRename(oldName, newName, 0.75);
    }
}
