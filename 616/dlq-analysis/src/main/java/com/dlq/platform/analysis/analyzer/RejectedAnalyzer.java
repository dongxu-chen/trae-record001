package com.dlq.platform.analysis.analyzer;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.api.Rules;
import org.jeasy.rules.api.RulesEngine;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class RejectedAnalyzer extends AbstractDeadLetterAnalyzer {

    private final Rules rules = new Rules();

    public RejectedAnalyzer(RulesEngine rulesEngine) {
        this.rulesEngine = rulesEngine;
    }

    @Override
    public boolean support(DeadLetterMessage message) {
        String deadReason = message.getDeadReason();
        if (deadReason == null) {
            return false;
        }
        return deadReason.contains("Rejected")
                || deadReason.contains("rejected")
                || deadReason.contains("拒绝")
                || deadReason.contains("队列满")
                || deadReason.contains("线程池")
                || deadReason.contains("ThreadPoolExecutor")
                || deadReason.contains("BlockingQueue");
    }

    @Override
    protected Rules getRules() {
        return rules;
    }

    @Override
    public AnalysisResult analyze(DeadLetterMessage message) {
        Map<String, Object> details = new HashMap<>();
        double confidence = 0.5;
        String rootCause = "消息消费被拒绝";
        String suggestedAction = "检查队列堆积情况，调整线程池配置";
        List<String> repairSteps = new ArrayList<>();

        String deadReason = message.getDeadReason();
        String stackTrace = message.getStackTrace();

        if (deadReason != null) {
            if (deadReason.contains("队列满") || deadReason.contains("queue is full")) {
                confidence = 0.95;
                rootCause = "消息队列已满，新消息被拒绝";
                suggestedAction = "立即扩容队列容量或增加消费者数量";
                repairSteps.add("检查当前队列深度和消费速率");
                repairSteps.add("增加消费者实例数量");
                repairSteps.add("临时扩容队列容量");
                repairSteps.add("考虑消息降级或丢弃非关键消息");
                details.put("rejectType", "QUEUE_FULL");
            } else if (deadReason.contains("线程池") || deadReason.contains("ThreadPoolExecutor")) {
                confidence = 0.9;
                rootCause = "消费线程池饱和，任务被拒绝策略处理";
                suggestedAction = "调整线程池参数或增加处理能力";
                repairSteps.add("检查线程池配置（核心线程数、最大线程数、队列类型）");
                repairSteps.add("适当调大核心线程数和最大线程数");
                repairSteps.add("优化消费逻辑，减少单条消息处理时间");
                repairSteps.add("考虑使用更合理的拒绝策略（如CallerRunsPolicy）");
                details.put("rejectType", "THREAD_POOL_EXHAUSTED");
            } else if (deadReason.contains("RejectedExecutionException")) {
                confidence = 0.85;
                rootCause = "线程池执行器拒绝执行任务";
                suggestedAction = "检查线程池状态和系统负载";
                repairSteps.add("监控系统CPU、内存使用率");
                repairSteps.add("检查线程池是否已关闭或耗尽");
                repairSteps.add("考虑限流或熔断机制");
                details.put("rejectType", "REJECTED_EXECUTION");
            }
        }

        if (stackTrace != null && stackTrace.contains("Capacity")) {
            confidence = Math.min(confidence + 0.1, 1.0);
            details.put("capacityIssue", true);
        }

        Integer retryCount = message.getRetryCount();
        if (retryCount != null) {
            details.put("retryCount", retryCount);
            if (retryCount > 5) {
                confidence = Math.min(confidence + 0.05, 1.0);
            }
        }

        if (repairSteps.isEmpty()) {
            repairSteps.add("检查消息中间件日志，确认拒绝原因");
            repairSteps.add("监控系统资源使用情况");
            repairSteps.add("验证消费者是否正常运行");
        }

        return AnalysisResult.builder()
                .reasonType(DeadReasonTypeEnum.REJECTED)
                .confidence(confidence)
                .rootCause(rootCause)
                .suggestedAction(suggestedAction)
                .repairSteps(repairSteps)
                .details(details)
                .build();
    }

    @Override
    protected DeadReasonTypeEnum getDeadReasonType() {
        return DeadReasonTypeEnum.REJECTED;
    }

    @Override
    protected AlertLevelEnum getDefaultRiskLevel() {
        return AlertLevelEnum.CRITICAL;
    }
}
