package com.datasecurity.masking;

import com.datasecurity.masking.enums.MaskStrategy;
import com.datasecurity.masking.rule.CustomMaskRule;
import com.datasecurity.masking.rule.RuleManagementService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class RuleManagementServiceTest {

    @Autowired
    private RuleManagementService ruleManagementService;

    @Test
    void testGetAllRules() {
        List<CustomMaskRule> rules = ruleManagementService.getAllRules();
        assertTrue(rules.size() >= 15, "Should have at least 15 builtin rules");
    }

    @Test
    void testGetEnabledRules() {
        List<CustomMaskRule> rules = ruleManagementService.getEnabledRules();
        assertTrue(rules.size() > 0);
        for (CustomMaskRule rule : rules) {
            assertTrue(rule.isEnabled());
        }
    }

    @Test
    void testGetRuleById() {
        CustomMaskRule rule = ruleManagementService.getRuleById("builtin_phone");
        assertNotNull(rule);
        assertEquals("手机号", rule.getName());
        assertEquals(MaskStrategy.MASK, rule.getDefaultStrategy());
        assertEquals(3, rule.getKeepStart());
        assertEquals(4, rule.getKeepEnd());
    }

    @Test
    void testMatchByColumnName() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("phone_number", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("phone"));

        rule = ruleManagementService.matchByColumn("id_card", "身份证号");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("id_card"));

        rule = ruleManagementService.matchByColumn("bank_card", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("bank_card"));

        rule = ruleManagementService.matchByColumn("user_name", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("name"));

        rule = ruleManagementService.matchByColumn("email_address", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("email"));
    }

    @Test
    void testMatchByComment() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("col1", "用户的手机号码");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("phone"));

        rule = ruleManagementService.matchByColumn("col2", "银行卡号码");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("bank_card"));
    }

    @Test
    void testMatchByValue() {
        CustomMaskRule rule = ruleManagementService.matchByValue("13800138000");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("phone"));

        rule = ruleManagementService.matchByValue("110101199001011234");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("id_card"));

        rule = ruleManagementService.matchByValue("6222021234567890123");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("bank_card"));

        rule = ruleManagementService.matchByValue("test@example.com");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("email"));
    }

    @Test
    void testPassportRule() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("passport_no", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("passport"));
        assertEquals(MaskStrategy.MASK, rule.getDefaultStrategy());
        assertEquals(2, rule.getKeepStart());
        assertEquals(2, rule.getKeepEnd());
    }

    @Test
    void testCreditCardRule() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("credit_card", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("credit_card"));
    }

    @Test
    void testPasswordRule() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("user_password", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("password"));
        assertEquals(MaskStrategy.REPLACE, rule.getDefaultStrategy());
        assertEquals("******", rule.getReplaceValue());
    }

    @Test
    void testLicensePlateRule() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("plate_number", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("license_plate"));
    }

    @Test
    void testQQRule() {
        CustomMaskRule rule = ruleManagementService.matchByValue("123456789");
        assertNotNull(rule);
        assertTrue(rule.getId().contains("qq"));
    }

    @Test
    void testWechatRule() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("wechat_id", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("wechat"));
    }

    @Test
    void testSalaryRule() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("monthly_salary", null);
        assertNotNull(rule);
        assertTrue(rule.getId().contains("salary"));
        assertEquals(MaskStrategy.REPLACE, rule.getDefaultStrategy());
    }

    @Test
    void testAddAndRemoveCustomRule() {
        CustomMaskRule customRule = CustomMaskRule.builder()
                .id("custom_test_rule")
                .name("测试规则")
                .columnKeywords(List.of("test_col", "测试列"))
                .valueRegex("^TEST[0-9]+$")
                .defaultStrategy(MaskStrategy.MASK)
                .maskChar("#")
                .keepStart(2)
                .keepEnd(2)
                .enabled(true)
                .priority(100)
                .build();

        ruleManagementService.addRule(customRule);

        CustomMaskRule found = ruleManagementService.getRuleById("custom_test_rule");
        assertNotNull(found);
        assertEquals("测试规则", found.getName());

        CustomMaskRule matched = ruleManagementService.matchByColumn("test_col", null);
        assertNotNull(matched);
        assertEquals("custom_test_rule", matched.getId());

        boolean removed = ruleManagementService.removeRule("custom_test_rule");
        assertTrue(removed);

        found = ruleManagementService.getRuleById("custom_test_rule");
        assertNull(found);
    }

    @Test
    void testNoMatch() {
        CustomMaskRule rule = ruleManagementService.matchByColumn("abc_def", null);
        assertNull(rule);

        rule = ruleManagementService.matchByValue("random_text_123");
        assertNull(rule);
    }
}
