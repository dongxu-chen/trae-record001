package com.coupon.controller;

import com.coupon.clickhouse.service.EffectEvaluationService;
import com.coupon.common.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/v1/evaluation")
public class EvaluationController {

    private final EffectEvaluationService evaluationService;

    public EvaluationController(EffectEvaluationService evaluationService) {
        this.evaluationService = evaluationService;
    }

    @GetMapping("/overall")
    public ApiResponse<EffectEvaluationService.CouponEffectStats> getOverallStats(
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        log.info("Get overall stats: {} to {}", startDate, endDate);
        EffectEvaluationService.CouponEffectStats stats =
                evaluationService.getOverallStats(startDate, endDate);
        if (stats == null) {
            return ApiResponse.error("获取统计数据失败");
        }
        return ApiResponse.success(stats);
    }

    @GetMapping("/experiment/{experimentId}/groups")
    public ApiResponse<List<EffectEvaluationService.ExperimentGroupStats>> getExperimentGroupStats(
            @PathVariable String experimentId,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        log.info("Get experiment group stats: {} from {} to {}", experimentId, startDate, endDate);
        List<EffectEvaluationService.ExperimentGroupStats> stats =
                evaluationService.getExperimentGroupStats(experimentId, startDate, endDate);
        return ApiResponse.success(stats);
    }

    @GetMapping("/experiment/{experimentId}/compare")
    public ApiResponse<EffectEvaluationService.ExperimentComparison> compareExperiment(
            @PathVariable String experimentId,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        log.info("Compare experiment: {} from {} to {}", experimentId, startDate, endDate);
        EffectEvaluationService.ExperimentComparison comparison =
                evaluationService.compareExperiments(experimentId, startDate, endDate);
        return ApiResponse.success(comparison);
    }

    @GetMapping("/daily")
    public ApiResponse<List<EffectEvaluationService.DailyStats>> getDailyStats(
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate,
            @RequestParam(required = false) String experimentId,
            @RequestParam(required = false) String groupId) {
        log.info("Get daily stats: {} to {}, exp={}, group={}",
                startDate, endDate, experimentId, groupId);
        List<EffectEvaluationService.DailyStats> stats =
                evaluationService.getDailyStats(startDate, endDate, experimentId, groupId);
        return ApiResponse.success(stats);
    }

    @GetMapping("/actions")
    public ApiResponse<Map<Integer, EffectEvaluationService.ActionPerformance>> getActionPerformance(
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        log.info("Get action performance: {} to {}", startDate, endDate);
        Map<Integer, EffectEvaluationService.ActionPerformance> stats =
                evaluationService.getActionPerformanceStats(startDate, endDate);
        return ApiResponse.success(stats);
    }

    @GetMapping("/summary")
    public ApiResponse<Map<String, Object>> getSummary(
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        log.info("Get summary: {} to {}", startDate, endDate);

        EffectEvaluationService.CouponEffectStats overall =
                evaluationService.getOverallStats(startDate, endDate);

        EffectEvaluationService.ExperimentComparison comparison =
                evaluationService.compareExperiments("default_coupon_exp", startDate, endDate);

        Map<Integer, EffectEvaluationService.ActionPerformance> actions =
                evaluationService.getActionPerformanceStats(startDate, endDate);

        EffectEvaluationService.ActionPerformance bestAction = actions.values().stream()
                .max((a, b) -> Double.compare(a.getRoi(), b.getRoi()))
                .orElse(null);

        return ApiResponse.success(Map.of(
                "overall", overall,
                "experiment_comparison", comparison,
                "best_action", bestAction,
                "action_count", actions.size()
        ));
    }
}
