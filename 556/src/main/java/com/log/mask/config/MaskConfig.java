package com.log.mask.config;

import com.log.mask.core.MaskRule;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

public class MaskConfig {
    private final Properties properties = new Properties();
    private String logFormat = "text";
    private final List<MaskRule> customRules = new ArrayList<>();
    private boolean enableDefaultRules = true;
    private String regexEngine = "dfa";

    public MaskConfig() {
    }

    public void loadFromFile(String configPath) throws IOException {
        try (InputStream is = getClass().getClassLoader().getResourceAsStream(configPath)) {
            if (is != null) {
                properties.load(is);
                parseProperties();
            }
        }
    }

    private void parseProperties() {
        String format = properties.getProperty("log.format");
        if (format != null && !format.isEmpty()) {
            this.logFormat = format;
        }

        String enableDefault = properties.getProperty("rules.default.enable");
        if (enableDefault != null) {
            this.enableDefaultRules = Boolean.parseBoolean(enableDefault);
        }

        String engine = properties.getProperty("regex.engine");
        if (engine != null && !engine.isEmpty()) {
            this.regexEngine = engine;
        }

        int ruleIndex = 1;
        while (true) {
            String name = properties.getProperty("rules.custom." + ruleIndex + ".name");
            if (name == null) {
                break;
            }
            String regex = properties.getProperty("rules.custom." + ruleIndex + ".regex");
            String groupIndex = properties.getProperty("rules.custom." + ruleIndex + ".groupIndex");
            String replacement = properties.getProperty("rules.custom." + ruleIndex + ".replacement");
            String enabled = properties.getProperty("rules.custom." + ruleIndex + ".enabled", "true");
            String priority = properties.getProperty("rules.custom." + ruleIndex + ".priority", "0");

            if (regex != null && replacement != null) {
                MaskRule rule = new MaskRule();
                rule.setName(name);
                rule.setRegex(regex);
                rule.setGroupIndex(Integer.parseInt(groupIndex != null ? groupIndex : "0"));
                rule.setReplacement(replacement);
                rule.setEnabled(Boolean.parseBoolean(enabled));
                rule.setPriority(Integer.parseInt(priority));
                customRules.add(rule);
            }
            ruleIndex++;
        }
    }

    public String getLogFormat() {
        return logFormat;
    }

    public void setLogFormat(String logFormat) {
        this.logFormat = logFormat;
    }

    public List<MaskRule> getCustomRules() {
        return customRules;
    }

    public boolean isEnableDefaultRules() {
        return enableDefaultRules;
    }

    public void setEnableDefaultRules(boolean enableDefaultRules) {
        this.enableDefaultRules = enableDefaultRules;
    }

    public String getRegexEngine() {
        return regexEngine;
    }

    public void setRegexEngine(String regexEngine) {
        this.regexEngine = regexEngine;
    }

    public boolean isUseDFA() {
        return "dfa".equalsIgnoreCase(regexEngine);
    }

    public String getProperty(String key) {
        return properties.getProperty(key);
    }

    public String getProperty(String key, String defaultValue) {
        return properties.getProperty(key, defaultValue);
    }
}
