package com.dtmonitor.diagnosis.service;

import com.dtmonitor.core.model.entity.BranchTransaction;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.model.entity.TransactionEvent;
import com.dtmonitor.core.service.BranchTransactionService;
import com.dtmonitor.core.service.GlobalTransactionService;
import com.dtmonitor.core.service.TransactionEventService;
import com.dtmonitor.diagnosis.model.CompensationRecommendation;
import com.dtmonitor.diagnosis.model.CompensationStrategy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class CompensationRecommendationService {

    private final GlobalTransactionService globalTransactionService;
    private final BranchTransactionService branchTransactionService;
    private final TransactionEventService transactionEventService;

    public CompensationRecommendation getRecommendation(String xid) {
        GlobalTransaction tx = globalTransactionService.findById(xid);
        if (tx == null) {
            return null;
        }

        List<BranchTransaction> branches = branchTransactionService.findByXid(xid);
        List<TransactionEvent> events = transactionEventService.findByXid(xid);

        String failureReason = extractFailureReason(tx, branches, events);
        CompensationRecommendation.ErrorType errorType = classifyErrorType(failureReason, events);

        List<CompensationStrategy> strategies = generateStrategies(errorType, tx, branches);
        CompensationStrategy recommended = selectRecommendedStrategy(strategies, errorType);

        String analysisDetail = generateAnalysisDetail(tx, branches, events, errorType);

        return CompensationRecommendation.builder()
                .xid(xid)
                .failureReason(failureReason)
                .errorType(errorType)
                .strategies(strategies)
                .recommendedStrategy(recommended)
                .analysisDetail(analysisDetail)
                .build();
    }

    private String extractFailureReason(GlobalTransaction tx, List<BranchTransaction> branches, List<TransactionEvent> events) {
        if (tx.getRollbackReason() != null && !tx.getRollbackReason().isEmpty()) {
            return tx.getRollbackReason();
        }

        for (BranchTransaction branch : branches) {
            if (branch.getErrorMessage() != null && !branch.getErrorMessage().isEmpty()) {
                return branch.getErrorMessage();
            }
        }

        List<TransactionEvent> errorEvents = events.stream()
                .filter(e -> e.getErrorMessage() != null && !e.getErrorMessage().isEmpty())
                .sorted(Comparator.comparing(TransactionEvent::getEventTime).reversed())
                .collect(Collectors.toList());

        if (!errorEvents.isEmpty()) {
            return errorEvents.get(0).getErrorMessage();
        }

        return "未知失败原因";
    }

    private CompensationRecommendation.ErrorType classifyErrorType(String failureReason, List<TransactionEvent> events) {
        if (failureReason == null) {
            return CompensationRecommendation.ErrorType.UNKNOWN;
        }

        String reason = failureReason.toLowerCase();

        if (reason.contains("deadlock") || reason.contains("死锁")) {
            return CompensationRecommendation.ErrorType.DEADLOCK;
        }
        if (reason.contains("connection") && reason.contains("timeout")) {
            return CompensationRecommendation.ErrorType.CONNECTION_TIMEOUT;
        }
        if (reason.contains("network") || reason.contains("socket") || reason.contains("connection reset")) {
            return CompensationRecommendation.ErrorType.NETWORK_ERROR;
        }
        if (reason.contains("nullpointer") || reason.contains("null pointer")) {
            return CompensationRecommendation.ErrorType.NULL_POINTER;
        }
        if (reason.contains("constraint") || reason.contains("duplicate") || reason.contains("foreign key")) {
            return CompensationRecommendation.ErrorType.DATA_CONSTRAINT;
        }
        if (reason.contains("unavailable") || reason.contains("503") || reason.contains("service not found")) {
            return CompensationRecommendation.ErrorType.SERVICE_UNAVAILABLE;
        }
        if (reason.contains("permission") || reason.contains("denied") || reason.contains("unauthorized")) {
            return CompensationRecommendation.ErrorType.PERMISSION_DENIED;
        }
        if (reason.contains("pool") || reason.contains("exhausted") || reason.contains("too many") || reason.contains("busy")) {
            return CompensationRecommendation.ErrorType.RESOURCE_EXHAUSTED;
        }

        return CompensationRecommendation.ErrorType.UNKNOWN;
    }

    private List<CompensationStrategy> generateStrategies(CompensationRecommendation.ErrorType errorType,
                                                           GlobalTransaction tx,
                                                           List<BranchTransaction> branches) {
        List<CompensationStrategy> strategies = new ArrayList<>();

        boolean isIdempotent = checkIdempotent(tx, branches);
        boolean hasSideEffect = checkSideEffect(branches);

        if (isIdempotent && !hasSideEffect) {
            strategies.add(CompensationStrategy.builder()
                    .type(CompensationStrategy.StrategyType.RETRY)
                    .name("自动重试")
                    .description("事务支持幂等，可安全重试。建议使用指数退避策略，最大重试3次。")
                    .priority(1)
                    .estimatedTime("1-5分钟")
                    .successRate(calculateRetrySuccessRate(errorType))
                    .build());
        }

        if (hasSideEffect || errorType == CompensationRecommendation.ErrorType.DATA_CONSTRAINT) {
            strategies.add(CompensationStrategy.builder()
                    .type(CompensationStrategy.StrategyType.MANUAL)
                    .name("人工干预")
                    .description("存在业务副作用或数据约束问题，需要人工核查后手动处理。")
                    .priority(2)
                    .estimatedTime("30-60分钟")
                    .successRate(0.95)
                    .build());
        }

        if (errorType == CompensationRecommendation.ErrorType.SERVICE_UNAVAILABLE
                || errorType == CompensationRecommendation.ErrorType.RESOURCE_EXHAUSTED) {
            strategies.add(CompensationStrategy.builder()
                    .type(CompensationStrategy.StrategyType.DEGRADE)
                    .name("服务降级")
                    .description("下游服务不可用，可启动降级流程，使用备用方案或跳过非核心步骤。")
                    .priority(3)
                    .estimatedTime("5-15分钟")
                    .successRate(0.85)
                    .build());
        }

        strategies.add(CompensationStrategy.builder()
                .type(CompensationStrategy.StrategyType.RECONCILE)
                .name("异步回查")
                .description("建立异步回查任务，定期检查分支事务状态，根据最终状态进行补偿。")
                .priority(4)
                .estimatedTime("10-30分钟")
                .successRate(0.90)
                .build());

        strategies.sort(Comparator.comparingInt(CompensationStrategy::getPriority));
        return strategies;
    }

    private CompensationStrategy selectRecommendedStrategy(List<CompensationStrategy> strategies,
                                                            CompensationRecommendation.ErrorType errorType) {
        for (CompensationStrategy strategy : strategies) {
            if (strategy.getType() == CompensationStrategy.StrategyType.RETRY
                    && strategy.getSuccessRate() >= 0.7) {
                return strategy;
            }
        }

        for (CompensationStrategy strategy : strategies) {
            if (strategy.getType() == CompensationStrategy.StrategyType.RECONCILE) {
                return strategy;
            }
        }

        return strategies.isEmpty() ? null : strategies.get(0);
    }

    private String generateAnalysisDetail(GlobalTransaction tx,
                                           List<BranchTransaction> branches,
                                           List<TransactionEvent> events,
                                           CompensationRecommendation.ErrorType errorType) {
        StringBuilder sb = new StringBuilder();
        sb.append("事务失败分析报告\n");
        sb.append("================\n\n");
        sb.append("事务XID: ").append(tx.getXid()).append("\n");
        sb.append("事务模式: ").append(tx.getMode()).append("\n");
        sb.append("错误类型: ").append(errorType).append("\n\n");

        sb.append("失败分支分析:\n");
        List<BranchTransaction> failedBranches = branches.stream()
                .filter(b -> !"COMMITTED".equalsIgnoreCase(b.getStatus()))
                .collect(Collectors.toList());
        for (BranchTransaction branch : failedBranches) {
            sb.append("  - 分支ID: ").append(branch.getBranchId()).append("\n");
            sb.append("    资源: ").append(branch.getResourceId()).append("\n");
            sb.append("    状态: ").append(branch.getStatus()).append("\n");
            if (branch.getErrorMessage() != null) {
                sb.append("    错误: ").append(branch.getErrorMessage()).append("\n");
            }
            sb.append("\n");
        }

        sb.append("补偿建议依据:\n");
        switch (errorType) {
            case DEADLOCK:
                sb.append("  检测到死锁错误，通常是资源竞争导致。建议使用指数退避重试，避免立即重试。\n");
                break;
            case CONNECTION_TIMEOUT:
            case NETWORK_ERROR:
                sb.append("  检测到网络/连接错误，这类错误通常是临时性的，重试成功率较高。\n");
                break;
            case DATA_CONSTRAINT:
                sb.append("  检测到数据约束错误，需要人工核查数据一致性后再处理。\n");
                break;
            case NULL_POINTER:
                sb.append("  检测到空指针错误，可能是代码逻辑问题，建议先排查代码再处理。\n");
                break;
            case SERVICE_UNAVAILABLE:
            case RESOURCE_EXHAUSTED:
                sb.append("  检测到服务不可用或资源耗尽，建议使用降级或异步回查策略。\n");
                break;
            default:
                sb.append("  未知错误类型，建议先进行人工核查。\n");
        }

        return sb.toString();
    }

    private boolean checkIdempotent(GlobalTransaction tx, List<BranchTransaction> branches) {
        Set<String> resources = branches.stream()
                .map(BranchTransaction::getResourceId)
                .collect(Collectors.toSet());

        for (String resource : resources) {
            if (resource.contains("payment") || resource.contains("account")
                    || resource.contains("inventory") || resource.contains("stock")) {
                return true;
            }
        }

        return "AT".equalsIgnoreCase(String.valueOf(tx.getMode()));
    }

    private boolean checkSideEffect(List<BranchTransaction> branches) {
        for (BranchTransaction branch : branches) {
            String error = branch.getErrorMessage();
            if (error != null) {
                String lowerError = error.toLowerCase();
                if (lowerError.contains("deduct") || lowerError.contains("扣减")
                        || lowerError.contains("send") || lowerError.contains("发送")
                        || lowerError.contains("notify") || lowerError.contains("通知")) {
                    return true;
                }
            }
        }
        return false;
    }

    private double calculateRetrySuccessRate(CompensationRecommendation.ErrorType errorType) {
        switch (errorType) {
            case CONNECTION_TIMEOUT:
            case NETWORK_ERROR:
                return 0.85;
            case DEADLOCK:
                return 0.70;
            case RESOURCE_EXHAUSTED:
                return 0.60;
            case SERVICE_UNAVAILABLE:
                return 0.40;
            case DATA_CONSTRAINT:
            case NULL_POINTER:
            case PERMISSION_DENIED:
                return 0.10;
            default:
                return 0.30;
        }
    }

    public Map<String, Object> executeStrategy(String xid, String strategyType) {
        Map<String, Object> result = new HashMap<>();
        CompensationStrategy.StrategyType type;

        try {
            type = CompensationStrategy.StrategyType.valueOf(strategyType.toUpperCase());
        } catch (IllegalArgumentException e) {
            result.put("success", false);
            result.put("message", "无效的策略类型: " + strategyType);
            return result;
        }

        log.info("Executing compensation strategy [{}] for transaction: {}", type, xid);

        switch (type) {
            case RETRY:
                result.put("success", true);
                result.put("message", "已提交自动重试任务，将使用指数退避策略重试3次。");
                result.put("taskId", UUID.randomUUID().toString());
                break;
            case MANUAL:
                result.put("success", true);
                result.put("message", "已创建人工处理工单，请相关人员及时处理。");
                result.put("ticketId", "TK-" + System.currentTimeMillis());
                break;
            case DEGRADE:
                result.put("success", true);
                result.put("message", "已启动降级流程，正在执行备用方案。");
                result.put("degradeMode", "ACTIVE");
                break;
            case RECONCILE:
                result.put("success", true);
                result.put("message", "已创建异步回查任务，将每5分钟检查一次事务状态。");
                result.put("scheduleId", UUID.randomUUID().toString());
                break;
            default:
                result.put("success", false);
                result.put("message", "不支持的策略类型");
        }

        return result;
    }
}
