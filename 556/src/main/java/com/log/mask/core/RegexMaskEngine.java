package com.log.mask.core;

import com.log.mask.core.dfa.DFAMatcher;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class RegexMaskEngine {
    private final List<MaskRule> rules = new ArrayList<>();
    private final DFAMatcher dfaMatcher = new DFAMatcher();
    private boolean useDFA = true;
    private boolean needRecompile = true;

    public RegexMaskEngine() {
        loadDefaultRules();
    }

    private void loadDefaultRules() {
        for (MaskPattern pattern : MaskPattern.values()) {
            addRule(new MaskRule(pattern.getName(), pattern.getRegex(),
                pattern.getGroupIndex(), pattern.getReplacement(), pattern.getPriority()));
        }
    }

    public void addRule(MaskRule rule) {
        rules.add(rule);
        dfaMatcher.addPattern(rule.getName(), rule.getRegex(), 
            rule.getGroupIndex(), rule.getReplacement(), rule.getPriority());
        needRecompile = true;
    }

    public void addRules(List<MaskRule> ruleList) {
        for (MaskRule rule : ruleList) {
            addRule(rule);
        }
    }

    public String mask(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }

        if (useDFA) {
            if (needRecompile) {
                dfaMatcher.compile();
                needRecompile = false;
            }
            return dfaMatcher.mask(input);
        } else {
            String result = input;
            List<MaskRule> sortedRules = getSortedRules();
            for (MaskRule rule : sortedRules) {
                if (rule.isEnabled()) {
                    result = applyRule(result, rule);
                }
            }
            return result;
        }
    }

    private List<MaskRule> getSortedRules() {
        List<MaskRule> sortedRules = new ArrayList<>(rules);
        sortedRules.sort((a, b) -> Integer.compare(b.getPriority(), a.getPriority()));
        return sortedRules;
    }

    private String applyRule(String input, MaskRule rule) {
        Pattern pattern = Pattern.compile(rule.getRegex(), Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(input);
        StringBuffer sb = new StringBuffer();
        while (matcher.find()) {
            if (rule.getGroupIndex() > 0) {
                if (rule.getGroupIndex() <= matcher.groupCount()) {
                    String matched = matcher.group(rule.getGroupIndex());
                    String masked = maskString(matched);
                    matcher.appendReplacement(sb, matcher.group().replace(matched, masked));
                }
            } else {
                String replacement = processReplacement(matcher, rule.getReplacement());
                matcher.appendReplacement(sb, replacement);
            }
        }
        matcher.appendTail(sb);
        return sb.toString();
    }

    private String processReplacement(Matcher matcher, String replacement) {
        String result = replacement;
        for (int i = 1; i <= matcher.groupCount(); i++) {
            String groupValue = matcher.group(i);
            if (groupValue != null) {
                result = result.replace("$" + i, groupValue);
            }
        }
        return result;
    }

    private String maskString(String str) {
        if (str.length() <= 2) {
            return "*";
        }
        return str.charAt(0) + "****" + str.charAt(str.length() - 1);
    }

    public List<MaskRule> getRules() {
        List<MaskRule> sortedRules = getSortedRules();
        return new ArrayList<>(sortedRules);
    }

    public void clearRules() {
        rules.clear();
        dfaMatcher.clear();
        needRecompile = true;
    }

    public boolean isUseDFA() {
        return useDFA;
    }

    public void setUseDFA(boolean useDFA) {
        this.useDFA = useDFA;
    }

    public DFAMatcher getDfaMatcher() {
        return dfaMatcher;
    }

    public long benchmark(String input, int iterations, boolean useDFA) {
        boolean originalDFA = this.useDFA;
        this.useDFA = useDFA;
        if (useDFA) {
            dfaMatcher.compile();
        }

        long startTime = System.nanoTime();
        for (int i = 0; i < iterations; i++) {
            mask(input);
        }
        long endTime = System.nanoTime();

        this.useDFA = originalDFA;
        return endTime - startTime;
    }

    public String getPerformanceReport(String input, int iterations) {
        long dfaTime = benchmark(input, iterations, true);
        long nfaTime = benchmark(input, iterations, false);
        double speedup = (double) nfaTime / dfaTime;

        StringBuilder sb = new StringBuilder();
        sb.append("=== 性能报告 ===\n");
        sb.append(String.format("测试数据长度: %d 字符\n", input.length()));
        sb.append(String.format("迭代次数: %d\n", iterations));
        sb.append(String.format("DFA 引擎耗时: %.3f ms\n", dfaTime / 1_000_000.0));
        sb.append(String.format("NFA 引擎耗时: %.3f ms\n", nfaTime / 1_000_000.0));
        sb.append(String.format("性能提升: %.1f 倍\n", speedup));
        sb.append(String.format("DFA 状态: %s\n", dfaMatcher.isUseDFA() ? "启用" : "禁用"));
        sb.append("================\n");
        return sb.toString();
    }
}
