package com.log.mask.core.dfa;

import dk.brics.automaton.*;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class DFAMatcher {
    private final Map<String, PatternInfo> patternMap = new LinkedHashMap<>();
    private Automaton combinedAutomaton;
    private Map<String, Automaton> automatonMap = new HashMap<>();
    private boolean useDFA = true;
    private final Map<String, Pattern> nfaPatternCache = new HashMap<>();

    private static class PatternInfo {
        String regex;
        int groupIndex;
        String replacement;
        int priority;
        boolean isComplex;

        PatternInfo(String regex, int groupIndex, String replacement, int priority) {
            this.regex = regex;
            this.groupIndex = groupIndex;
            this.replacement = replacement;
            this.priority = priority;
            this.isComplex = isComplexRegex(regex);
        }
    }

    private static boolean isComplexRegex(String regex) {
        return regex.contains("(?") || regex.contains("\\b") || regex.contains("(?i)") 
                || regex.contains("$") || regex.contains("^") || regex.contains("|") 
                || regex.contains("*?") || regex.contains("+?");
    }

    public void addPattern(String name, String regex, int groupIndex, String replacement, int priority) {
        patternMap.put(name, new PatternInfo(regex, groupIndex, replacement, priority));
        if (!isComplexRegex(regex)) {
            try {
                String simplifiedRegex = simplifyRegex(regex);
                RegExp regExp = new RegExp(simplifiedRegex);
                Automaton automaton = regExp.toAutomaton();
                automatonMap.put(name, automaton);
            } catch (Exception e) {
                patternMap.get(name).isComplex = true;
            }
        }
        buildCombinedAutomaton();
    }

    private String simplifyRegex(String regex) {
        String simplified = regex.replace("(?i)", "");
        simplified = simplified.replace("\\b", "");
        simplified = simplified.replace("\\d", "[0-9]");
        simplified = simplified.replace("\\w", "[a-zA-Z0-9_]");
        simplified = simplified.replace("\\s", "[ \t\n\r]");
        return simplified;
    }

    private void buildCombinedAutomaton() {
        if (automatonMap.isEmpty()) {
            combinedAutomaton = Automaton.makeEmpty();
            return;
        }
        List<Automaton> automata = new ArrayList<>(automatonMap.values());
        combinedAutomaton = Automaton.union(automata);
        combinedAutomaton.minimize();
    }

    public void compile() {
        for (Map.Entry<String, PatternInfo> entry : patternMap.entrySet()) {
            if (entry.getValue().isComplex) {
                nfaPatternCache.put(entry.getKey(), 
                    Pattern.compile(entry.getValue().regex, Pattern.CASE_INSENSITIVE));
            }
        }
        buildCombinedAutomaton();
    }

    public String mask(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }

        String result = input;
        List<MaskRule> sortedRules = getSortedRules();

        for (MaskRule rule : sortedRules) {
            PatternInfo info = patternMap.get(rule.name);
            if (info == null) continue;

            if (info.isComplex || !useDFA) {
                result = applyNFARule(result, rule.name, info);
            } else {
                result = applyDFARule(result, rule.name, info);
            }
        }
        return result;
    }

    private List<MaskRule> getSortedRules() {
        List<MaskRule> rules = new ArrayList<>();
        for (Map.Entry<String, PatternInfo> entry : patternMap.entrySet()) {
            rules.add(new MaskRule(entry.getKey(), entry.getValue().priority));
        }
        rules.sort((a, b) -> Integer.compare(b.priority, a.priority));
        return rules;
    }

    private static class MaskRule {
        String name;
        int priority;

        MaskRule(String name, int priority) {
            this.name = name;
            this.priority = priority;
        }
    }

    private String applyDFARule(String input, String name, PatternInfo info) {
        Automaton automaton = automatonMap.get(name);
        if (automaton == null) {
            return applyNFARule(input, name, info);
        }

        StringBuilder result = new StringBuilder();
        int lastEnd = 0;
        int inputLength = input.length();

        for (int i = 0; i < inputLength; i++) {
            RunAutomaton runAutomaton = new RunAutomaton(automaton, true);
            int state = runAutomaton.getInitialState();
            int matchEnd = -1;

            for (int j = i; j < inputLength; j++) {
                state = runAutomaton.step(state, input.charAt(j));
                if (state == -1) break;
                if (runAutomaton.isAccept(state)) {
                    matchEnd = j + 1;
                }
            }

            if (matchEnd != -1) {
                String matched = input.substring(i, matchEnd);
                if (lastEnd < i) {
                    result.append(input, lastEnd, i);
                }
                String replacement = processReplacement(matched, info);
                result.append(replacement);
                lastEnd = matchEnd;
                i = matchEnd - 1;
            }
        }

        if (lastEnd < inputLength) {
            result.append(input, lastEnd, inputLength);
        }

        return result.toString();
    }

    private String applyNFARule(String input, String name, PatternInfo info) {
        Pattern pattern = nfaPatternCache.get(name);
        if (pattern == null) {
            pattern = Pattern.compile(info.regex, Pattern.CASE_INSENSITIVE);
            nfaPatternCache.put(name, pattern);
        }

        Matcher matcher = pattern.matcher(input);
        StringBuffer sb = new StringBuffer();
        while (matcher.find()) {
            if (info.groupIndex > 0 && info.groupIndex <= matcher.groupCount()) {
                String matched = matcher.group(info.groupIndex);
                String masked = maskString(matched);
                matcher.appendReplacement(sb, matcher.group().replace(matched, masked));
            } else {
                String replacement = processReplacement(matcher, info);
                matcher.appendReplacement(sb, replacement);
            }
        }
        matcher.appendTail(sb);
        return sb.toString();
    }

    private String processReplacement(String matched, PatternInfo info) {
        if (info.groupIndex > 0) {
            return maskString(matched);
        }
        return info.replacement;
    }

    private String processReplacement(Matcher matcher, PatternInfo info) {
        String result = info.replacement;
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

    public boolean isUseDFA() {
        return useDFA;
    }

    public void setUseDFA(boolean useDFA) {
        this.useDFA = useDFA;
    }

    public void clear() {
        patternMap.clear();
        automatonMap.clear();
        nfaPatternCache.clear();
        combinedAutomaton = null;
    }

    public List<String> getPatternNames() {
        return new ArrayList<>(patternMap.keySet());
    }

    public boolean hasPattern(String name) {
        return patternMap.containsKey(name);
    }

    public void removePattern(String name) {
        patternMap.remove(name);
        automatonMap.remove(name);
        nfaPatternCache.remove(name);
        buildCombinedAutomaton();
    }
}
