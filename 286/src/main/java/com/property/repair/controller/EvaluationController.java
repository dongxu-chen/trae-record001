package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.dto.EvaluationDTO;
import com.property.repair.entity.RepairEvaluation;
import com.property.repair.service.EvaluationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/evaluation")
@CrossOrigin
public class EvaluationController {

    @Autowired
    private EvaluationService evaluationService;

    @PostMapping("/submit")
    public Result<RepairEvaluation> submit(@Validated @RequestBody EvaluationDTO dto) {
        try {
            RepairEvaluation evaluation = evaluationService.evaluate(dto);
            return Result.success(evaluation);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/order/{orderId}")
    public Result<RepairEvaluation> getByOrderId(@PathVariable Long orderId) {
        return Result.success(evaluationService.getByOrderId(orderId));
    }

    @GetMapping("/worker/{workerId}")
    public Result<List<RepairEvaluation>> getWorkerEvaluations(@PathVariable Long workerId) {
        return Result.success(evaluationService.getWorkerEvaluations(workerId));
    }
}
