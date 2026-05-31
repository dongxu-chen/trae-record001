package com.log.mask;

import com.log.mask.audit.*;
import com.log.mask.config.MaskConfig;
import com.log.mask.core.MaskRule;
import com.log.mask.discovery.*;
import com.log.mask.dynamic.*;
import com.log.mask.parser.LogParser;
import com.log.mask.parser.LogParserFactory;
import com.log.mask.rule.RuleEngine;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.List;

public class LogDesensitizationService {
    private static final Logger logger = LoggerFactory.getLogger(LogDesensitizationService.class);
    
    private final RuleEngine ruleEngine;
    private LogParser logParser;
    private final MaskConfig config;
    private final SensitiveDataFinder dataFinder;
    private final DynamicMaskEngine dynamicMaskEngine;
    private final AuditLogger auditLogger;

    public LogDesensitizationService() {
        this(new MaskConfig());
    }

    public LogDesensitizationService(MaskConfig config) {
        this.config = config;
        this.ruleEngine = new RuleEngine();
        this.logParser = LogParserFactory.getParser(config.getLogFormat());
        this.dataFinder = new SensitiveDataFinder();
        this.dynamicMaskEngine = new DynamicMaskEngine();
        this.auditLogger = new AuditLogger();
        initializeRules();
    }

    public LogDesensitizationService(String configPath) throws IOException {
        this.config = new MaskConfig();
        this.config.loadFromFile(configPath);
        this.ruleEngine = new RuleEngine();
        this.logParser = LogParserFactory.getParser(config.getLogFormat());
        this.dataFinder = new SensitiveDataFinder();
        this.dynamicMaskEngine = new DynamicMaskEngine();
        this.auditLogger = new AuditLogger();
        initializeRules();
    }

    private void initializeRules() {
        if (!config.isEnableDefaultRules()) {
            ruleEngine.clearAllRules();
        }
        List<MaskRule> customRules = config.getCustomRules();
        if (customRules != null && !customRules.isEmpty()) {
            ruleEngine.addRules(customRules);
        }
        ruleEngine.getMaskEngine().setUseDFA(config.isUseDFA());
        logger.info("LogDesensitizationService initialized with {} enabled rules, engine: {}", 
            ruleEngine.getEnabledRules().size(), 
            config.isUseDFA() ? "DFA (高性能)" : "NFA (兼容模式)");
    }

    public String mask(String logContent) {
        return logParser.parseAndMask(logContent, ruleEngine.getMaskEngine());
    }

    public String mask(String logContent, String format) {
        LogParser parser = LogParserFactory.getParser(format);
        return parser.parseAndMask(logContent, ruleEngine.getMaskEngine());
    }

    public String maskDynamic(String logContent, AccessContext context) {
        String masked = dynamicMaskEngine.mask(logContent, context);
        if (auditLogger.isEnabled() && !masked.equals(logContent)) {
            auditLogger.logMaskOperation(
                context.getUserId(),
                "dynamic",
                MaskAction.MASK_DYNAMIC.getDefaultReason(),
                MaskAction.MASK_DYNAMIC,
                preview(logContent, 50),
                preview(masked, 50),
                "dynamic"
            );
        }
        return masked;
    }

    public String maskDynamic(String logContent, String format, AccessContext context) {
        LogParser parser = LogParserFactory.getParser(format);
        String parsed = parser.parseAndMask(logContent, ruleEngine.getMaskEngine());
        return dynamicMaskEngine.mask(parsed, context);
    }

    public DiscoveryReport scan(String logContent) {
        DiscoveryReport report = dataFinder.scan(logContent);
        if (auditLogger.isEnabled() && report.hasSensitiveData()) {
            auditLogger.logMaskOperation(
                "system",
                "scan",
                MaskAction.DISCOVER.getDefaultReason(),
                MaskAction.DISCOVER,
                preview(logContent, 50),
                "发现 " + report.getTotalCount() + " 处敏感数据",
                "scanner"
            );
        }
        return report;
    }

    public DiscoveryReport scan(String logContent, String source) {
        DiscoveryReport report = dataFinder.scan(logContent, source);
        if (auditLogger.isEnabled() && report.hasSensitiveData()) {
            auditLogger.logMaskOperation(
                "system",
                "scan",
                MaskAction.DISCOVER.getDefaultReason(),
                MaskAction.DISCOVER,
                preview(logContent, 50),
                "发现 " + report.getTotalCount() + " 处敏感数据",
                source
            );
        }
        return report;
    }

    private String preview(String text, int maxLen) {
        if (text == null) return "";
        return text.length() <= maxLen ? text : text.substring(0, maxLen) + "...";
    }

    public void addCustomRule(MaskRule rule) {
        ruleEngine.addRule(rule);
        if (auditLogger.isEnabled()) {
            auditLogger.logMaskOperation(
                "admin",
                rule.getName(),
                MaskAction.RULE_ADD.getDefaultReason(),
                MaskAction.RULE_ADD,
                rule.getRegex(),
                rule.getReplacement(),
                "rule-engine"
            );
        }
    }

    public void removeRule(String ruleName) {
        if (auditLogger.isEnabled()) {
            auditLogger.logMaskOperation(
                "admin",
                ruleName,
                MaskAction.RULE_REMOVE.getDefaultReason(),
                MaskAction.RULE_REMOVE,
                "",
                "",
                "rule-engine"
            );
        }
        ruleEngine.removeRule(ruleName);
    }

    public void enableRule(String ruleName) {
        ruleEngine.enableRule(ruleName);
    }

    public void disableRule(String ruleName) {
        ruleEngine.disableRule(ruleName);
    }

    public List<MaskRule> getAllRules() {
        return ruleEngine.getAllRules();
    }

    public void setLogFormat(String format) {
        this.logParser = LogParserFactory.getParser(format);
    }

    public void resetToDefault() {
        ruleEngine.resetToDefault();
        logParser = LogParserFactory.getParser("text");
    }

    public RuleEngine getRuleEngine() {
        return ruleEngine;
    }

    public MaskConfig getConfig() {
        return config;
    }

    public SensitiveDataFinder getDataFinder() {
        return dataFinder;
    }

    public DynamicMaskEngine getDynamicMaskEngine() {
        return dynamicMaskEngine;
    }

    public AuditLogger getAuditLogger() {
        return auditLogger;
    }

    public void setAuditStorage(AuditStorage storage) {
        auditLogger.setStorage(storage);
    }

    public AuditStatistics getAuditStatistics() {
        return auditLogger.getStatistics();
    }
}
