package com.dlq.platform.analysis.generator;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class SuggestionGenerator {

    private static final Map<DeadReasonTypeEnum, String[]> DEFAULT_ACTIONS = new EnumMap<>(DeadReasonTypeEnum.class);
    private static final Map<DeadReasonTypeEnum, String[]> DEFAULT_REPAIR_STEPS = new EnumMap<>(DeadReasonTypeEnum.class);

    static {
        DEFAULT_ACTIONS.put(DeadReasonTypeEnum.FORMAT_ERROR, new String[]{
                "检查消息格式", "验证JSON结构", "修复数据类型"
        });
        DEFAULT_ACTIONS.put(DeadReasonTypeEnum.BIZ_EXCEPTION, new String[]{
                "检查业务逻辑", "修复代码Bug", "处理异常情况"
        });
        DEFAULT_ACTIONS.put(DeadReasonTypeEnum.TIMEOUT, new String[]{
                "检查依赖服务", "优化处理逻辑", "调整超时配置"
        });
        DEFAULT_ACTIONS.put(DeadReasonTypeEnum.REJECTED, new String[]{
                "检查系统资源", "扩容队列/线程池", "调整拒绝策略"
        });
        DEFAULT_ACTIONS.put(DeadReasonTypeEnum.OTHER, new String[]{
                "进一步分析原因", "查看详细日志", "人工介入处理"
        });

        DEFAULT_REPAIR_STEPS.put(DeadReasonTypeEnum.FORMAT_ERROR, new String[]{
                "1. 使用JSON校验工具验证消息格式",
                "2. 检查必填字段是否完整",
                "3. 确认数据类型是否正确",
                "4. 修复格式错误后重新发送"
        });
        DEFAULT_REPAIR_STEPS.put(DeadReasonTypeEnum.BIZ_EXCEPTION, new String[]{
                "1. 分析异常堆栈信息",
                "2. 定位问题代码位置",
                "3. 修复业务逻辑Bug",
                "4. 部署修复版本",
                "5. 重新消费死信消息"
        });
        DEFAULT_REPAIR_STEPS.put(DeadReasonTypeEnum.TIMEOUT, new String[]{
                "1. 检查下游服务健康状态",
                "2. 分析处理耗时瓶颈",
                "3. 优化业务处理逻辑",
                "4. 调整超时时间配置",
                "5. 考虑增加重试机制"
        });
        DEFAULT_REPAIR_STEPS.put(DeadReasonTypeEnum.REJECTED, new String[]{
                "1. 检查队列堆积情况",
                "2. 监控系统资源使用",
                "3. 扩容消费者实例",
                "4. 调整线程池参数",
                "5. 考虑限流或降级"
        });
        DEFAULT_REPAIR_STEPS.put(DeadReasonTypeEnum.OTHER, new String[]{
                "1. 收集更多上下文信息",
                "2. 分析相关系统日志",
                "3. 联系相关开发人员",
                "4. 根据具体情况处理"
        });
    }

    public AnalysisResult enhanceSuggestion(AnalysisResult result) {
        if (result == null) {
            return null;
        }

        DeadReasonTypeEnum reasonType = result.getReasonType();
        if (reasonType == null) {
            reasonType = DeadReasonTypeEnum.OTHER;
        }

        if (result.getSuggestedAction() == null || result.getSuggestedAction().isEmpty()) {
            String[] actions = DEFAULT_ACTIONS.get(reasonType);
            if (actions != null && actions.length > 0) {
                result.setSuggestedAction(actions[0]);
            }
        }

        if (result.getRepairSteps() == null || result.getRepairSteps().isEmpty()) {
            String[] steps = DEFAULT_REPAIR_STEPS.get(reasonType);
            if (steps != null) {
                result.setRepairSteps(new ArrayList<>(Arrays.asList(steps)));
            }
        } else {
            List<String> existingSteps = result.getRepairSteps();
            Set<String> stepSet = new LinkedHashSet<>(existingSteps);
            String[] defaultSteps = DEFAULT_REPAIR_STEPS.get(reasonType);
            if (defaultSteps != null) {
                for (String step : defaultSteps) {
                    stepSet.add(step);
                }
            }
            result.setRepairSteps(new ArrayList<>(stepSet));
        }

        if (result.getRootCause() == null || result.getRootCause().isEmpty()) {
            result.setRootCause(generateDefaultRootCause(reasonType, result));
        }

        if (result.getDetails() == null) {
            result.setDetails(new HashMap<>());
        }
        result.getDetails().put("suggestionGenerated", true);
        result.getDetails().put("suggestionVersion", "1.0.0");

        return result;
    }

    public String generateSuggestedAction(DeadReasonTypeEnum reasonType, Map<String, Object> details) {
        String[] actions = DEFAULT_ACTIONS.get(reasonType);
        if (actions != null && actions.length > 0) {
            return actions[0];
        }
        return "请进一步分析";
    }

    public List<String> generateRepairSteps(DeadReasonTypeEnum reasonType, Map<String, Object> details) {
        String[] steps = DEFAULT_REPAIR_STEPS.get(reasonType);
        if (steps != null) {
            return new ArrayList<>(Arrays.asList(steps));
        }
        return Collections.emptyList();
    }

    public String generateDetailedSuggestion(AnalysisResult result) {
        StringBuilder sb = new StringBuilder();
        sb.append("【问题分析】\n");
        sb.append("原因类型: ").append(result.getReasonType() != null ? result.getReasonType().getDesc() : "未知").append("\n");
        sb.append("置信度: ").append(String.format("%.1f%%", result.getConfidence() * 100)).append("\n");
        sb.append("根本原因: ").append(result.getRootCause()).append("\n\n");

        sb.append("【处理建议】\n");
        sb.append(result.getSuggestedAction()).append("\n\n");

        sb.append("【修复步骤】\n");
        List<String> repairSteps = result.getRepairSteps();
        if (repairSteps != null && !repairSteps.isEmpty()) {
            for (int i = 0; i < repairSteps.size(); i++) {
                sb.append(i + 1).append(". ").append(repairSteps.get(i)).append("\n");
            }
        }

        sb.append("\n【详细信息】\n");
        Map<String, Object> details = result.getDetails();
        if (details != null && !details.isEmpty()) {
            for (Map.Entry<String, Object> entry : details.entrySet()) {
                sb.append(entry.getKey()).append(": ").append(entry.getValue()).append("\n");
            }
        }

        return sb.toString();
    }

    private String generateDefaultRootCause(DeadReasonTypeEnum reasonType, AnalysisResult result) {
        return switch (reasonType) {
            case FORMAT_ERROR -> "消息格式存在问题，需要检查消息体结构";
            case BIZ_EXCEPTION -> "业务处理过程中发生异常，需要检查业务逻辑";
            case TIMEOUT -> "消息处理超时，可能是下游服务响应慢或处理逻辑复杂";
            case REJECTED -> "消息被拒绝，可能是系统资源不足或队列已满";
            case OTHER -> "未知原因，需要进一步分析";
        };
    }
}
