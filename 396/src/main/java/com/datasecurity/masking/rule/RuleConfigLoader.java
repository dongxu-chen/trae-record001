package com.datasecurity.masking.rule;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Component
public class RuleConfigLoader {

    @Value("${data-masking.rules.config-path:classpath:rules/}")
    private String rulesConfigPath;

    private List<CustomMaskRule> builtinRules;

    @PostConstruct
    public void init() {
        builtinRules = loadBuiltinRules();
        log.info("Loaded {} builtin masking rules", builtinRules.size());

        try {
            List<CustomMaskRule> customRules = loadCustomRules();
            builtinRules.addAll(customRules);
            log.info("Loaded {} custom masking rules", customRules.size());
        } catch (Exception e) {
            log.warn("No custom rules found or failed to load", e);
        }
    }

    private List<CustomMaskRule> loadBuiltinRules() {
        List<CustomMaskRule> rules = new ArrayList<>();

        rules.add(CustomMaskRule.builder()
                .id("builtin_id_card")
                .name("身份证号")
                .description("中华人民共和国居民身份证号")
                .columnKeywords(List.of("id_card", "idcard", "idCard", "身份证", "身份证号", "身份证号码", "id_no", "idno"))
                .commentKeywords(List.of("身份证", "身份号", "证件号"))
                .valueRegex("^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(6)
                .keepEnd(4)
                .enabled(true)
                .priority(100)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_phone")
                .name("手机号")
                .description("中国大陆手机号码")
                .columnKeywords(List.of("phone", "mobile", "telephone", "手机号", "手机号码", "电话", "联系电话", "cellphone"))
                .commentKeywords(List.of("手机", "电话", "联系电话"))
                .valueRegex("^1[3-9]\\d{9}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(3)
                .keepEnd(4)
                .enabled(true)
                .priority(100)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_bank_card")
                .name("银行卡号")
                .description("银行卡号")
                .columnKeywords(List.of("bank_card", "bankcard", "银行卡", "银行卡号", "银行卡号码", "card_no", "cardno", "account_no"))
                .commentKeywords(List.of("银行卡", "卡号", "账号"))
                .valueRegex("^[1-9]\\d{12,18}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(4)
                .keepEnd(4)
                .enabled(true)
                .priority(100)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_name")
                .name("姓名")
                .description("中文姓名")
                .columnKeywords(List.of("name", "username", "姓名", "用户姓名", "客户姓名", "real_name", "realname"))
                .commentKeywords(List.of("姓名", "名字", "用户名"))
                .valueRegex("^[\\u4e00-\\u9fa5]{2,4}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(1)
                .keepEnd(0)
                .enabled(true)
                .priority(100)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_email")
                .name("邮箱")
                .description("电子邮箱地址")
                .columnKeywords(List.of("email", "mail", "邮箱", "电子邮箱"))
                .commentKeywords(List.of("邮箱", "邮件", "email"))
                .valueRegex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(2)
                .keepEnd(0)
                .enabled(true)
                .priority(100)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_address")
                .name("地址")
                .description("居住/收货地址")
                .columnKeywords(List.of("address", "addr", "地址", "住址", "居住地址", "收货地址"))
                .commentKeywords(List.of("地址", "住址", "收货地"))
                .valueRegex(null)
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.TRUNCATE)
                .keepStart(6)
                .replaceValue("***")
                .enabled(true)
                .priority(100)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_passport")
                .name("护照号")
                .description("护照号码")
                .columnKeywords(List.of("passport", "passport_no", "护照", "护照号", "护照号码"))
                .commentKeywords(List.of("护照", "护照号"))
                .valueRegex("^[A-Za-z0-9]{5,17}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(2)
                .keepEnd(2)
                .enabled(true)
                .priority(90)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_credit_card")
                .name("信用卡号")
                .description("信用卡号")
                .columnKeywords(List.of("credit_card", "creditCard", "信用卡", "信用卡号"))
                .commentKeywords(List.of("信用卡", "信用额度"))
                .valueRegex("^4[0-9]{12}(?:[0-9]{3})?$|^5[1-5][0-9]{14}$|^3[47][0-9]{13}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(4)
                .keepEnd(4)
                .enabled(true)
                .priority(90)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_social_security")
                .name("社保号")
                .description("社会保险号")
                .columnKeywords(List.of("social_security", "socialSecurity", "社保", "社保号", "社会保险号"))
                .commentKeywords(List.of("社保", "社保号"))
                .valueRegex("^\\d{10,20}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(3)
                .keepEnd(4)
                .enabled(true)
                .priority(80)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_license_plate")
                .name("车牌号")
                .description("车牌号码")
                .columnKeywords(List.of("license_plate", "plate_number", "车牌", "车牌号", "车牌号码"))
                .commentKeywords(List.of("车牌", "车牌号"))
                .valueRegex("^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,5}[A-Z0-9挂学警港澳]$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(2)
                .keepEnd(2)
                .enabled(true)
                .priority(80)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_tax_id")
                .name("税号")
                .description("纳税人识别号")
                .columnKeywords(List.of("tax_id", "taxId", "税号", "纳税人识别号", "统一社会信用代码"))
                .commentKeywords(List.of("税号", "纳税人", "统一信用代码"))
                .valueRegex("^[A-Za-z0-9]{15,20}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(3)
                .keepEnd(4)
                .enabled(true)
                .priority(80)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_qq")
                .name("QQ号")
                .description("QQ号码")
                .columnKeywords(List.of("qq", "qq_no", "qq号", "QQ号", "qq号码"))
                .commentKeywords(List.of("QQ", "qq号"))
                .valueRegex("^[1-9][0-9]{4,10}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(2)
                .keepEnd(2)
                .enabled(true)
                .priority(70)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_wechat")
                .name("微信号")
                .description("微信号")
                .columnKeywords(List.of("wechat", "wechat_id", "wx_id", "微信", "微信号"))
                .commentKeywords(List.of("微信", "微信号"))
                .valueRegex("^[a-zA-Z][a-zA-Z0-9_-]{5,19}$")
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(2)
                .keepEnd(2)
                .enabled(true)
                .priority(70)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_password")
                .name("密码")
                .description("密码字段")
                .columnKeywords(List.of("password", "pwd", "passwd", "密码", "用户密码"))
                .commentKeywords(List.of("密码", "口令"))
                .valueRegex(null)
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.REPLACE)
                .replaceValue("******")
                .enabled(true)
                .priority(100)
                .build());

        rules.add(CustomMaskRule.builder()
                .id("builtin_salary")
                .name("薪资")
                .description("工资金额")
                .columnKeywords(List.of("salary", "wage", "薪资", "工资", "月薪", "年薪"))
                .commentKeywords(List.of("薪资", "工资", "薪水"))
                .valueRegex(null)
                .defaultStrategy(com.datasecurity.masking.enums.MaskStrategy.REPLACE)
                .replaceValue("***")
                .enabled(true)
                .priority(80)
                .build());

        for (CustomMaskRule rule : rules) {
            if (rule.getValueRegex() != null && !rule.getValueRegex().isEmpty()) {
                rule.setValuePattern(Pattern.compile(rule.getValueRegex()));
            }
        }

        return rules;
    }

    private List<CustomMaskRule> loadCustomRules() throws Exception {
        List<CustomMaskRule> rules = new ArrayList<>();

        PathMatchingResourcePatternResolver resolver = new PathMatchingResourcePatternResolver();
        Resource[] resources = resolver.getResources(rulesConfigPath + "*.json");

        for (Resource resource : resources) {
            log.info("Loading custom rules from: {}", resource.getFilename());
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8))) {
                String json = reader.lines().collect(Collectors.joining("\n"));
                CustomMaskRule rule = parseRuleJson(json);
                if (rule != null && rule.isEnabled()) {
                    if (rule.getValueRegex() != null && !rule.getValueRegex().isEmpty()) {
                        rule.setValuePattern(Pattern.compile(rule.getValueRegex()));
                    }
                    rules.add(rule);
                }
            }
        }

        return rules;
    }

    private CustomMaskRule parseRuleJson(String json) {
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.readValue(json, CustomMaskRule.class);
        } catch (Exception e) {
            log.error("Failed to parse rule json", e);
            return null;
        }
    }

    public List<CustomMaskRule> getAllRules() {
        return new ArrayList<>(builtinRules);
    }

    public List<CustomMaskRule> getEnabledRules() {
        return builtinRules.stream()
                .filter(CustomMaskRule::isEnabled)
                .sorted((a, b) -> Integer.compare(
                        b.getPriority() != null ? b.getPriority() : 0,
                        a.getPriority() != null ? a.getPriority() : 0))
                .collect(Collectors.toList());
    }

    public CustomMaskRule getRuleById(String ruleId) {
        return builtinRules.stream()
                .filter(r -> ruleId.equals(r.getId()))
                .findFirst()
                .orElse(null);
    }

    public void addCustomRule(CustomMaskRule rule) {
        if (rule.getValueRegex() != null && !rule.getValueRegex().isEmpty()) {
            rule.setValuePattern(Pattern.compile(rule.getValueRegex()));
        }
        builtinRules.add(rule);
        log.info("Added custom rule: {} ({})", rule.getName(), rule.getId());
    }

    public boolean removeRule(String ruleId) {
        boolean removed = builtinRules.removeIf(r -> ruleId.equals(r.getId()));
        if (removed) {
            log.info("Removed rule: {}", ruleId);
        }
        return removed;
    }
}
