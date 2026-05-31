package com.dlq.platform.analysis.rules;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.annotation.Action;
import org.jeasy.rules.annotation.Condition;
import org.jeasy.rules.annotation.Fact;
import org.jeasy.rules.annotation.Rule;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@Rule(name = "TimeoutRule", description = "超时规则", priority = 5)
public class TimeoutRule {

    private static final String[] TIMEOUT_PATTERNS = {
            "SocketTimeoutException", "ReadTimeoutException",
            "ConnectTimeoutException", "TimeoutException",
            "RequestTimeoutException", "GatewayTimeout",
            "feign.RetryableException"
    };

    @Condition
    public boolean checkTimeout(@Fact("message") DeadLetterMessage message) {
        String stackTrace = message.getStackTrace();
        String deadReason = message.getDeadReason();

        for (String pattern : TIMEOUT_PATTERNS) {
            if (stackTrace != null && stackTrace.contains(pattern)) {
                return true;
            }
            if (deadReason != null && deadReason.contains(pattern)) {
                return true;
            }
        }

        Integer retryCount = message.getRetryCount();
        return retryCount != null && retryCount > 5;
    }

    @Action
    public void applyRule(@Fact("message") DeadLetterMessage message,
                        @Fact("result") AnalysisResult result) {
        String stackTrace = message.getStackTrace();
        String deadReason = message.getDeadReason();
        List<String> repairSteps = new ArrayList<>();

        String rootCause = "消息消费超时";
        String timeoutType = "CONSUMPTION_TIMEOUT";
        double confidence = 0.8;

        if (stackTrace != null) {
            if (stackTrace.contains("SocketTimeout")) {
                rootCause = "网络连接超时";
                timeoutType = "SOCKET_TIMEOUT";
                confidence = 0.9;
                repairSteps.add("检查网络连接稳定性");
                repairSteps.add("调整连接超时时间");
                repairSteps.add("考虑添加降级策略");
            } else if (stackTrace.contains("ReadTimeout")) {
                rootCause = "读取数据超时";
                timeoutType = "READ_TIMEOUT";
                confidence = 0.85;
                repairSteps.add("检查下游服务响应速度");
                repairSteps.add("优化查询性能");
                repairSteps.add("考虑异步处理");
            } else if (stackTrace.contains("ConnectTimeout")) {
                rootCause = "建立连接超时";
                timeoutType = "CONNECT_TIMEOUT";
                confidence = 0.88;
                repairSteps.add("检查目标服务是否可用");
                repairSteps.add("验证网络防火墙配置");
                repairSteps.add("考虑熔断机制");
            }
        }

        if (deadReason != null && deadReason.contains("feign") || deadReason.contains("Feign")) {
            rootCause = "Feign调用超时";
            timeoutType = "FEIGN_TIMEOUT";
            confidence = 0.92;
            repairSteps.add("检查被调用服务状态");
            repairSteps.add("调整Feign超时配置");
            repairSteps.add("添加降级处理逻辑");
        }

        Integer retryCount = message.getRetryCount();
        if (retryCount != null && retryCount > 0) {
            result.getDetails().put("retryCount", retryCount);
            if (retryCount > 10) {
                confidence = Math.min(confidence + 0.05, 1.0);
                repairSteps.add("当前重试次数已达 " + retryCount + "次，建议人工介入");
            }
        }

        Map<String, Object> headers = message.getHeaders();
        if (headers != null && headers.containsKey("processTime")) {
            try {
                long processTime = Long.parseLong(headers.get("processTime").toString());
                Duration duration = Duration.ofMillis(processTime);
                result.getDetails().put("processTimeMs", processTime);
                result.getDetails().put("processTimeFormatted", formatDuration(duration));
                if (processTime > 30000) {
                    confidence = Math.min(confidence + 0.05, 1.0);
                }
            } catch (Exception ignored) {
            }
        }

        result.setRootCause(rootCause);
        result.setSuggestedAction("检查依赖服务可用性，优化处理逻辑");

        if (repairSteps.isEmpty()) {
            repairSteps.add("检查下游服务健康状态");
            repairSteps.add("分析消息处理逻辑");
            repairSteps.add("优化业务处理流程");
        }
        repairSteps.add("考虑增加超时时间或重试机制");
        repairSteps.add("修复后重新消费消息");

        result.getDetails().put("ruleName", "TimeoutRule");
        result.getDetails().put("timeoutType", timeoutType);
        result.setConfidence(Math.max(result.getConfidence(), confidence));
        result.setRepairSteps(repairSteps);
    }

    private String formatDuration(Duration duration) {
        long seconds = duration.getSeconds();
        long absSeconds = Math.abs(seconds);
        String positive = String.format(
                "%d:%02d:%02d",
                absSeconds / 3600,
                (absSeconds % 3600) / 60,
                absSeconds % 60);
        return seconds < 0 ? "-" + positive : positive;
    }
}
