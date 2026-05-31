package com.dlq.platform.analysis.rules;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.annotation.Action;
import org.jeasy.rules.annotation.Condition;
import org.jeasy.rules.annotation.Fact;
import org.jeasy.rules.annotation.Rule;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
@Rule(name = "DatabaseAccessRule", description = "数据库访问异常规则", priority = 4)
public class DatabaseAccessRule {

    private static final String[] DB_EXCEPTION_PATTERNS = {
            "SQLException", "SQLTimeoutException", "SQLTransientException",
            "SQLNonTransientException", "SQLRecoverableException",
            "MySQLTimeoutException", "OracleTimeoutException",
            "LockAcquisitionException",
            "无法获取数据库连接", "数据库连接超时",
            "deadlock", "Deadlock", "锁等待超时"
    };

    @Condition
    public boolean checkDbException(@Fact("message") DeadLetterMessage message) {
        String stackTrace = message.getStackTrace();
        String deadReason = message.getDeadReason();

        for (String pattern : DB_EXCEPTION_PATTERNS) {
            if (stackTrace != null && stackTrace.contains(pattern)) {
                return true;
            }
            if (deadReason != null && deadReason.contains(pattern)) {
                return true;
            }
        }
        return false;
    }

    @Action
    public void applyRule(@Fact("message") DeadLetterMessage message,
                        @Fact("result") AnalysisResult result) {
        String stackTrace = message.getStackTrace();
        String deadReason = message.getDeadReason();
        List<String> repairSteps = new ArrayList<>();

        String rootCause = "数据库访问异常";
        String dbIssueType = "DATABASE_ERROR";
        double confidence = 0.8;

        if (stackTrace != null) {
            if (stackTrace.contains("deadlock") || stackTrace.contains("Deadlock")) {
                rootCause = "数据库死锁异常";
                dbIssueType = "DEADLOCK";
                confidence = 0.9;
                repairSteps.add("检查SQL语句是否会导致死锁");
                repairSteps.add("优化事务隔离级别");
                repairSteps.add("调整锁获取顺序");
            } else if (stackTrace.contains("timeout") || stackTrace.contains("Timeout")) {
                rootCause = "数据库查询超时";
                dbIssueType = "QUERY_TIMEOUT";
                confidence = 0.85;
                repairSteps.add("检查SQL执行计划");
                repairSteps.add("添加或优化索引");
                repairSteps.add("考虑分页查询");
            } else if (stackTrace.contains("连接") || stackTrace.contains("connection")) {
                rootCause = "数据库连接异常";
                dbIssueType = "CONNECTION_ERROR";
                confidence = 0.8;
                repairSteps.add("检查数据库连接池配置");
                repairSteps.add("验证数据库服务是否正常");
                repairSteps.add("检查网络连接");
            }
        }

        if (deadReason != null) {
            if (deadReason.contains("唯一索引") || deadReason.contains("unique")) {
                rootCause = "唯一约束冲突";
                dbIssueType = "UNIQUE_CONSTRAINT";
                confidence = 0.95;
                repairSteps.add("检查重复数据");
                repairSteps.add("验证业务逻辑是否正确");
            }
        }

        result.setRootCause(rootCause);
        result.setSuggestedAction("检查数据库状态和SQL语句，修复后重试");

        if (repairSteps.isEmpty()) {
            repairSteps.add("检查数据库连接状态");
            repairSteps.add("分析SQL执行计划");
            repairSteps.add("优化慢查询");
            repairSteps.add("考虑添加重试机制");
        }
        repairSteps.add("修复后重新消费消息");

        result.getDetails().put("ruleName", "DatabaseAccessRule");
        result.getDetails().put("dbIssueType", dbIssueType);
        result.getDetails().put("stackTrace", stackTrace);
        result.setConfidence(Math.max(result.getConfidence(), confidence));
        result.setRepairSteps(repairSteps);
    }
}
