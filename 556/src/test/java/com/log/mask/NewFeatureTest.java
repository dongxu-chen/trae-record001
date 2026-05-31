package com.log.mask;

import com.log.mask.audit.*;
import com.log.mask.core.RegexMaskEngine;
import com.log.mask.discovery.*;
import com.log.mask.dynamic.*;
import com.log.mask.parser.*;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

public class NewFeatureTest {
    private LogDesensitizationService service;

    @Before
    public void setUp() {
        service = new LogDesensitizationService();
    }

    // ===== 敏感信息发现测试 =====

    @Test
    public void testDiscoverPhone() {
        String content = "联系人: 13812345678";
        DiscoveryReport report = service.scan(content);
        assertTrue(report.hasSensitiveData());
        assertTrue(report.getTotalCount() >= 1);
    }

    @Test
    public void testDiscoverIdCard() {
        String content = "身份证号: 110101199001011234";
        DiscoveryReport report = service.scan(content);
        assertTrue(report.hasSensitiveData());
        assertTrue(report.hasCriticalData());
    }

    @Test
    public void testDiscoverMultipleTypes() {
        String content = "手机: 13812345678, 身份证: 110101199001011234, 邮箱: test@example.com";
        DiscoveryReport report = service.scan(content);
        assertTrue(report.getTotalCount() >= 3);
    }

    @Test
    public void testDiscoverNoSensitiveData() {
        String content = "这是一条普通日志，没有敏感信息";
        DiscoveryReport report = service.scan(content);
        assertFalse(report.hasSensitiveData());
        assertEquals(0, report.getTotalCount());
    }

    @Test
    public void testDiscoverPassword() {
        String content = "password=MySecret123";
        DiscoveryReport report = service.scan(content);
        assertTrue(report.hasCriticalData());
    }

    @Test
    public void testDiscoverApiKey() {
        String content = "api_key=sk-abc123def456ghi789";
        DiscoveryReport report = service.scan(content);
        assertTrue(report.hasCriticalData());
    }

    @Test
    public void testDiscoverRiskLevel() {
        String criticalContent = "身份证: 110101199001011234";
        DiscoveryReport criticalReport = service.scan(criticalContent);
        assertEquals(DiscoveryReport.RiskLevel.CRITICAL, criticalReport.getRiskLevel());

        String safeContent = "普通日志信息";
        DiscoveryReport safeReport = service.scan(safeContent);
        assertEquals(DiscoveryReport.RiskLevel.NONE, safeReport.getRiskLevel());
    }

    @Test
    public void testDiscoverReportFormat() {
        String content = "手机: 13812345678";
        DiscoveryReport report = service.scan(content);
        String textReport = report.toTextReport();
        assertNotNull(textReport);
        assertTrue(textReport.contains("敏感信息扫描报告"));
    }

    // ===== 动态脱敏测试 =====

    @Test
    public void testAdminNoMasking() {
        String content = "手机号: 13812345678";
        AccessContext admin = AccessContext.admin("admin1");
        String result = service.maskDynamic(content, admin);
        assertTrue(result.contains("13812345678"));
    }

    @Test
    public void testAnonymousFullMasking() {
        String content = "手机号: 13812345678";
        AccessContext anon = AccessContext.anonymous();
        String result = service.maskDynamic(content, anon);
        assertFalse(result.contains("13812345678"));
    }

    @Test
    public void testOperatorPartialMasking() {
        String content = "手机号: 13812345678";
        AccessContext operator = AccessContext.operator("op1");
        String result = service.maskDynamic(content, operator);
        assertTrue(result.contains("138"));
        assertTrue(result.contains("5678"));
        assertFalse(result.contains("13812345678"));
    }

    @Test
    public void testViewerPartialMasking() {
        String content = "手机号: 13812345678";
        AccessContext viewer = AccessContext.viewer("viewer1");
        String result = service.maskDynamic(content, viewer);
        assertFalse(result.contains("13812345678"));
    }

    @Test
    public void testMaskPolicyResolution() {
        AccessContext admin = AccessContext.admin("a");
        assertEquals(MaskPolicy.FULL, admin.resolvePolicy("phone"));

        AccessContext operator = AccessContext.operator("o");
        assertEquals(MaskPolicy.PARTIAL, operator.resolvePolicy("phone"));

        AccessContext anon = AccessContext.anonymous();
        assertEquals(MaskPolicy.COMPLETE, anon.resolvePolicy("phone"));
    }

    @Test
    public void testCustomPermission() {
        AccessContext ctx = AccessContext.of("user1", "CUSTOM");
        ctx.addPermission("sensitive:partial:phone");
        assertEquals(MaskPolicy.PARTIAL, ctx.resolvePolicy("phone"));
        assertEquals(MaskPolicy.COMPLETE, ctx.resolvePolicy("idCard"));
    }

    // ===== 脱敏审计测试 =====

    @Test
    public void testAuditLogging() {
        service.maskDynamic("手机号: 13812345678", AccessContext.anonymous());
        assertTrue(service.getAuditLogger().getRecordCount() > 0);
    }

    @Test
    public void testAuditRecordContent() {
        service.maskDynamic("手机号: 13812345678", AccessContext.anonymous());
        java.util.List<AuditRecord> records = service.getAuditLogger().getRecords();
        assertFalse(records.isEmpty());
        AuditRecord last = records.get(records.size() - 1);
        assertNotNull(last.getOperator());
        assertNotNull(last.getAction());
        assertEquals(MaskAction.MASK_DYNAMIC, last.getAction());
    }

    @Test
    public void testAuditDiscoveryLogging() {
        service.scan("手机号: 13812345678");
        java.util.List<AuditRecord> records = service.getAuditLogger().getRecordsByAction(MaskAction.DISCOVER);
        assertFalse(records.isEmpty());
    }

    @Test
    public void testAuditRuleAddLogging() {
        service.addCustomRule(new com.log.mask.core.MaskRule("test", "test", 0, "***", 10));
        java.util.List<AuditRecord> records = service.getAuditLogger().getRecordsByAction(MaskAction.RULE_ADD);
        assertFalse(records.isEmpty());
    }

    @Test
    public void testAuditStatistics() {
        service.scan("手机号: 13812345678, 身份证: 110101199001011234");
        service.maskDynamic("手机号: 13812345678", AccessContext.anonymous());
        AuditStatistics stats = service.getAuditStatistics();
        assertNotNull(stats);
        assertTrue(stats.totalRecords > 0);
        String report = stats.toTextReport();
        assertTrue(report.contains("脱敏审计统计"));
    }

    @Test
    public void testAuditDisable() {
        service.getAuditLogger().setEnabled(false);
        long before = service.getAuditLogger().getRecordCount();
        service.maskDynamic("手机号: 13812345678", AccessContext.anonymous());
        long after = service.getAuditLogger().getRecordCount();
        assertEquals(before, after);
        service.getAuditLogger().setEnabled(true);
    }

    @Test
    public void testAuditFilterByOperator() {
        service.maskDynamic("手机号: 13812345678", AccessContext.of("userA", "TEST"));
        java.util.List<AuditRecord> records = service.getAuditLogger().getRecordsByOperator("userA");
        assertFalse(records.isEmpty());
    }

    @Test
    public void testAuditExport() {
        service.scan("手机号: 13812345678");
        String export = service.getAuditLogger().exportAsText();
        assertNotNull(export);
        assertTrue(export.length() > 0);
    }
}
