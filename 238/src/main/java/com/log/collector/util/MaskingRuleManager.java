package com.log.collector.util;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.io.monitor.FileAlterationListener;
import org.apache.commons.io.monitor.FileAlterationListenerAdaptor;
import org.apache.commons.io.monitor.FileAlterationMonitor;
import org.apache.commons.io.monitor.FileAlterationObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;

public class MaskingRuleManager {

    private static final Logger logger = LoggerFactory.getLogger(MaskingRuleManager.class);

    private static volatile MaskingRuleManager instance;

    private final ConcurrentHashMap<String, MaskingRule> rules = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private FileAlterationMonitor monitor;
    private String configFilePath;
    private volatile long lastModified = 0;

    private MaskingRuleManager() {
    }

    public static MaskingRuleManager getInstance() {
        if (instance == null) {
            synchronized (MaskingRuleManager.class) {
                if (instance == null) {
                    instance = new MaskingRuleManager();
                }
            }
        }
        return instance;
    }

    public void init(String configFilePath, boolean enableHotReload) throws Exception {
        this.configFilePath = configFilePath;
        loadRules();

        if (enableHotReload) {
            startFileWatcher();
        }

        logger.info("MaskingRuleManager initialized - rules count: {}, hotReload: {}",
                rules.size(), enableHotReload);
    }

    private void loadRules() throws IOException {
        File configFile = new File(configFilePath);
        if (!configFile.exists()) {
            logger.warn("Masking config file not found, using default rules");
            loadDefaultRules();
            return;
        }

        long currentModified = configFile.lastModified();
        if (currentModified == lastModified) {
            logger.debug("Config file not modified, skipping reload");
            return;
        }

        String content = new String(Files.readAllBytes(Paths.get(configFilePath)));
        JsonNode root = objectMapper.readTree(content);
        JsonNode rulesNode = root.get("rules");

        if (rulesNode != null && rulesNode.isArray()) {
            ConcurrentHashMap<String, MaskingRule> newRules = new ConcurrentHashMap<>();
            for (JsonNode ruleNode : rulesNode) {
                try {
                    MaskingRule rule = parseRule(ruleNode);
                    newRules.put(rule.getName(), rule);
                    logger.info("Loaded masking rule: {}", rule.getName());
                } catch (Exception e) {
                    logger.error("Failed to parse masking rule", e);
                }
            }

            rules.clear();
            rules.putAll(newRules);
            lastModified = currentModified;
            logger.info("Masking rules reloaded - total: {}", rules.size());
        }
    }

    private void loadDefaultRules() {
        rules.clear();

        rules.put("phone", new MaskingRule(
                "phone",
                "(?<!\\d)(1[3-9]\\d{9})(?!\\d)",
                "****",
                3, 4,
                true
        ));

        rules.put("idcard", new MaskingRule(
                "idcard",
                "(?<!\\d)([1-9]\\d{5}(19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx])(?!\\d)",
                "********",
                6, 4,
                true
        ));

        rules.put("email", new MaskingRule(
                "email",
                "(?<![a-zA-Z0-9._-])([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})(?![a-zA-Z0-9._-])",
                "*",
                1, 1,
                true
        ));

        logger.info("Default masking rules loaded");
    }

    private MaskingRule parseRule(JsonNode node) {
        String name = node.get("name").asText();
        String pattern = node.get("pattern").asText();
        String maskChar = node.has("maskChar") ? node.get("maskChar").asText() : "*";
        int keepPrefix = node.has("keepPrefix") ? node.get("keepPrefix").asInt() : 0;
        int keepSuffix = node.has("keepSuffix") ? node.get("keepSuffix").asInt() : 0;
        boolean enabled = node.has("enabled") ? node.get("enabled").asBoolean() : true;

        return new MaskingRule(name, pattern, maskChar, keepPrefix, keepSuffix, enabled);
    }

    private void startFileWatcher() throws Exception {
        File configFile = new File(configFilePath);
        File parentDir = configFile.getParentFile();
        if (parentDir == null) {
            parentDir = new File(".");
        }

        FileAlterationObserver observer = new FileAlterationObserver(parentDir);
        FileAlterationListener listener = new FileAlterationListenerAdaptor() {
            @Override
            public void onFileChange(File file) {
                if (file.getAbsolutePath().equals(configFile.getAbsolutePath())) {
                    logger.info("Masking config file changed, reloading...");
                    try {
                        loadRules();
                    } catch (Exception e) {
                        logger.error("Failed to reload masking rules", e);
                    }
                }
            }

            @Override
            public void onFileCreate(File file) {
                if (file.getAbsolutePath().equals(configFile.getAbsolutePath())) {
                    logger.info("Masking config file created, loading...");
                    try {
                        loadRules();
                    } catch (Exception e) {
                        logger.error("Failed to load masking rules", e);
                    }
                }
            }
        };

        observer.addListener(listener);
        monitor = new FileAlterationMonitor(5000, observer);
        monitor.start();
        logger.info("File watcher started for: {}", configFilePath);
    }

    public String applyMasking(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }

        String result = input;
        for (MaskingRule rule : rules.values()) {
            if (rule.isEnabled()) {
                result = rule.apply(result);
            }
        }
        return result;
    }

    public MaskingRule getRule(String name) {
        return rules.get(name);
    }

    public List<MaskingRule> getAllRules() {
        return new ArrayList<>(rules.values());
    }

    public void reload() throws IOException {
        loadRules();
    }

    public void close() {
        if (monitor != null) {
            try {
                monitor.stop();
                logger.info("File watcher stopped");
            } catch (Exception e) {
                logger.warn("Error stopping file monitor", e);
            }
        }
    }

    public static class MaskingRule {
        private final String name;
        private final Pattern pattern;
        private final String maskChar;
        private final int keepPrefix;
        private final int keepSuffix;
        private final boolean enabled;

        public MaskingRule(String name, String pattern, String maskChar,
                           int keepPrefix, int keepSuffix, boolean enabled) {
            this.name = name;
            this.pattern = Pattern.compile(pattern);
            this.maskChar = maskChar;
            this.keepPrefix = keepPrefix;
            this.keepSuffix = keepSuffix;
            this.enabled = enabled;
        }

        public String apply(String input) {
            StringBuffer sb = new StringBuffer();
            java.util.regex.Matcher matcher = pattern.matcher(input);

            while (matcher.find()) {
                String matched = matcher.group(1);
                String masked = maskValue(matched);
                matcher.appendReplacement(sb, masked);
            }
            matcher.appendTail(sb);

            return sb.toString();
        }

        private String maskValue(String value) {
            int length = value.length();
            if (length <= keepPrefix + keepSuffix) {
                return repeat(maskChar, length);
            }

            String prefix = value.substring(0, keepPrefix);
            String suffix = value.substring(length - keepSuffix);
            int maskLength = length - keepPrefix - keepSuffix;

            if (name.equals("email")) {
                int atIndex = value.indexOf('@');
                if (atIndex > 0) {
                    String username = value.substring(0, atIndex);
                    String domain = value.substring(atIndex);
                    if (username.length() <= 2) {
                        return repeat(maskChar, username.length()) + domain;
                    } else {
                        return username.substring(0, 1) + repeat(maskChar, username.length() - 2)
                                + username.substring(username.length() - 1) + domain;
                    }
                }
            }

            return prefix + repeat(maskChar, maskLength) + suffix;
        }

        private String repeat(String ch, int count) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < count; i++) {
                sb.append(ch);
            }
            return sb.toString();
        }

        public String getName() {
            return name;
        }

        public Pattern getPattern() {
            return pattern;
        }

        public boolean isEnabled() {
            return enabled;
        }
    }
}
