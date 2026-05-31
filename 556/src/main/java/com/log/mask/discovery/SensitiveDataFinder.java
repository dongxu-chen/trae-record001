package com.log.mask.discovery;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SensitiveDataFinder {
    private final List<SensitivePattern> patterns = new ArrayList<>();

    public SensitiveDataFinder() {
        loadDefaultPatterns();
    }

    private void loadDefaultPatterns() {
        addPattern(new SensitivePattern("phone", "1[3-9]\\d{9", 
            SensitiveLevel.HIGH, "手机号码"));
        addPattern(new SensitivePattern("idCard", "\\d{6}(19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]", 
            SensitiveLevel.CRITICAL, "身份证号码"));
        addPattern(new SensitivePattern("password", "(?i)(password|pwd|passwd)[=:]['\"]?[^'\"\\s,;]{4,}", 
            SensitiveLevel.CRITICAL, "密码凭据"));
        addPattern(new SensitivePattern("email", "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}", 
            SensitiveLevel.MEDIUM, "电子邮箱"));
        addPattern(new SensitivePattern("bankCard", "\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}", 
            SensitiveLevel.HIGH, "银行卡号"));
        addPattern(new SensitivePattern("ipAddress", "\\b(\\d{1,3}\\.){3}\\d{1,3}\\b", 
            SensitiveLevel.LOW, "IP地址"));
        addPattern(new SensitivePattern("apiKey", "(?i)(api[_-]?key|secret[_-]?key|token)[=:]['\"]?[^'\"\\s,;]{8,}", 
            SensitiveLevel.CRITICAL, "API密钥/令牌"));
        addPattern(new SensitivePattern("address", "(?i)(地址|address|addr)[=:]([^,;\\n]{6,50})", 
            SensitiveLevel.MEDIUM, "地址信息"));
    }

    public void addPattern(SensitivePattern pattern) {
        patterns.add(pattern);
    }

    public DiscoveryReport scan(String content) {
        return scan(content, "");
    }

    public DiscoveryReport scan(String content, String source) {
        DiscoveryReport report = new DiscoveryReport(source, content.length());

        for (SensitivePattern sp : patterns) {
            Pattern pattern = Pattern.compile(sp.getRegex(), Pattern.CASE_INSENSITIVE);
            Matcher matcher = pattern.matcher(content);

            while (matcher.find()) {
                String matchedText = matcher.group();
                SensitiveDataItem item = new SensitiveDataItem(
                    sp.getName(),
                    sp.getCategory(),
                    sp.getLevel(),
                    matcher.start(),
                    matcher.end(),
                    maskForReport(matchedText, sp.getLevel()),
                    matchedText.length()
                );
                report.addItem(item);
            }
        }

        report.finalizeReport();
        return report;
    }

    private String maskForReport(String text, SensitiveLevel level) {
        if (text.length() <= 4) {
            return "****";
        }
        switch (level) {
            case CRITICAL:
                return text.substring(0, 2) + "****";
            case HIGH:
                return text.substring(0, 3) + "****" + text.substring(text.length() - 2);
            case MEDIUM:
                return text.substring(0, 4) + "****";
            case LOW:
                return text.substring(0, Math.min(6, text.length())) + "...";
            default:
                return "****";
        }
    }

    public List<SensitivePattern> getPatterns() {
        return new ArrayList<>(patterns);
    }
}
