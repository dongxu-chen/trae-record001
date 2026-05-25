package com.property.repair.service;

import com.property.repair.dto.EvaluationDTO;
import com.property.repair.entity.RepairEvaluation;
import com.property.repair.entity.RepairOrder;
import com.property.repair.repository.RepairEvaluationRepository;
import com.property.repair.repository.RepairOrderRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class EvaluationService {

    @Autowired
    private RepairEvaluationRepository evaluationRepository;

    @Autowired
    private RepairOrderRepository orderRepository;

    @Autowired
    private RepairLogService logService;

    @Autowired
    private SatisfactionAlertService satisfactionAlertService;

    @Transactional
    public RepairEvaluation evaluate(EvaluationDTO dto) {
        RepairOrder order = orderRepository.findById(dto.getOrderId()).orElse(null);
        if (order == null) {
            throw new RuntimeException("工单不存在");
        }
        if (!"COMPLETED".equals(order.getStatus())) {
            throw new RuntimeException("只有已完成的工单才能评价");
        }

        RepairEvaluation existing = evaluationRepository.findByOrderId(dto.getOrderId());
        if (existing != null) {
            throw new RuntimeException("该工单已评价");
        }

        RepairEvaluation evaluation = new RepairEvaluation();
        evaluation.setOrderId(dto.getOrderId());
        evaluation.setOrderNo(order.getOrderNo());
        evaluation.setOwnerId(dto.getOwnerId());
        evaluation.setWorkerId(order.getWorkerId());
        evaluation.setRating(dto.getRating());
        evaluation.setComment(dto.getComment());
        evaluation = evaluationRepository.save(evaluation);

        order.setStatus("EVALUATED");
        orderRepository.save(order);

        logService.addLog(order, "评价", dto.getOwnerId(), "业主", 
            "评分：" + dto.getRating() + "分，评价内容：" + dto.getComment());

        satisfactionAlertService.checkAndCreateAlert(evaluation);

        return evaluation;
    }

    public RepairEvaluation getByOrderId(Long orderId) {
        return evaluationRepository.findByOrderId(orderId);
    }

    public List<RepairEvaluation> getWorkerEvaluations(Long workerId) {
        return evaluationRepository.findByWorkerId(workerId);
    }
}
