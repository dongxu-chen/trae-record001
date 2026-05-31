package com.log.mask;

import com.log.mask.core.MaskRule;
import com.log.mask.core.RegexMaskEngine;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

public class RegexMaskEngineTest {
    private RegexMaskEngine engine;

    @Before
    public void setUp() {
        engine = new RegexMaskEngine();
    }

    @Test
    public void testPasswordMask() {
        String input = "password=123456";
        String result = engine.mask(input);
        assertFalse(result.contains("123456"));
        assertTrue(result.contains("password"));
    }

    @Test
    public void testPhoneMask() {
        String input = "手机号:13812345678";
        String result = engine.mask(input);
        assertTrue(result.contains("138"));
        assertTrue(result.contains("****"));
        assertTrue(result.contains("5678"));
        assertFalse(result.contains("13812345678"));
    }

    @Test
    public void testIdCardMask() {
        String input = "身份证:110101199001011234";
        String result = engine.mask(input);
        assertTrue(result.contains("110101"));
        assertTrue(result.contains("********"));
        assertFalse(result.contains("19900101"));
    }

    @Test
    public void testEmailMask() {
        String input = "邮箱:test@example.com";
        String result = engine.mask(input);
        assertTrue(result.contains("***@"));
        assertTrue(result.contains("example.com"));
    }

    @Test
    public void testMultipleSensitiveData() {
        String input = "用户:张三, 电话:13987654321, 密码:abc123, 邮箱:user@test.com";
        String result = engine.mask(input);
        assertFalse(result.contains("13987654321"));
        assertFalse(result.contains("abc123"));
        assertFalse(result.contains("user@"));
        assertTrue(result.contains("张三"));
    }

    @Test
    public void testNullInput() {
        assertNull(engine.mask(null));
    }

    @Test
    public void testEmptyInput() {
        assertEquals("", engine.mask(""));
    }

    @Test
    public void testNoSensitiveData() {
        String input = "这是一条普通日志，没有敏感信息";
        String result = engine.mask(input);
        assertEquals(input, result);
    }

    @Test
    public void testPrioritySorting() {
        java.util.List<MaskRule> rules = engine.getRules();
        assertEquals(6, rules.size());
        assertTrue(rules.get(0).getPriority() >= rules.get(1).getPriority());
        assertEquals("password", rules.get(0).getName());
        assertEquals(100, rules.get(0).getPriority());
        assertEquals("idCard", rules.get(1).getName());
        assertEquals(90, rules.get(1).getPriority());
    }

    @Test
    public void testCustomPriorityRule() {
        engine.clearRules();
        engine.addRule(new MaskRule("low", "test", 0, "***", 10));
        engine.addRule(new MaskRule("high", "data", 0, "***", 100));
        
        java.util.List<MaskRule> rules = engine.getRules();
        assertEquals("high", rules.get(0).getName());
        assertEquals(100, rules.get(0).getPriority());
        assertEquals("low", rules.get(1).getName());
        assertEquals(10, rules.get(1).getPriority());
    }

    @Test
    public void testDFAEngine() {
        engine.setUseDFA(true);
        String input = "手机号:13812345678, 密码:123456";
        String result = engine.mask(input);
        assertFalse(result.contains("13812345678"));
        assertFalse(result.contains("123456"));
        assertTrue(engine.isUseDFA());
    }

    @Test
    public void testNFAEngine() {
        engine.setUseDFA(false);
        String input = "手机号:13812345678, 密码:123456";
        String result = engine.mask(input);
        assertFalse(result.contains("13812345678"));
        assertFalse(result.contains("123456"));
        assertFalse(engine.isUseDFA());
    }

    @Test
    public void testDFAPerformance() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 100; i++) {
            sb.append("用户").append(i).append(": 手机号=").append(13800000000L + i)
              .append(", 身份证=").append(110101199001010000L + i)
              .append(", 密码=pass").append(i).append("\n");
        }
        String bigLog = sb.toString();
        
        long dfaTime = engine.benchmark(bigLog, 100, true);
        long nfaTime = engine.benchmark(bigLog, 100, false);
        
        double speedup = (double) nfaTime / dfaTime;
        System.out.println("DFA time: " + dfaTime / 1_000_000.0 + "ms");
        System.out.println("NFA time: " + nfaTime / 1_000_000.0 + "ms");
        System.out.println("Speedup: " + speedup + "x");
        
        assertTrue(speedup >= 1.0);
    }

    @Test
    public void testConsistencyBetweenDFAAndNFA() {
        String input = "用户:张三, 电话:13987654321, 密码:abc123, 身份证:110101199001011234, 邮箱:test@example.com";
        
        engine.setUseDFA(true);
        String dfaResult = engine.mask(input);
        
        engine.setUseDFA(false);
        String nfaResult = engine.mask(input);
        
        assertEquals(dfaResult, nfaResult);
    }

    @Test
    public void testBankCardMask() {
        String input = "银行卡号:6222021234567890123";
        String result = engine.mask(input);
        assertTrue(result.contains("6222"));
        assertTrue(result.contains("********"));
        assertTrue(result.contains("0123"));
        assertFalse(result.contains("6222021234567890123"));
    }
}
