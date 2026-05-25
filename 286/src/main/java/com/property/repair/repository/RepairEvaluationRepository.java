package com.property.repair.repository;

import com.property.repair.entity.RepairEvaluation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RepairEvaluationRepository extends JpaRepository<RepairEvaluation, Long> {

    RepairEvaluation findByOrderId(Long orderId);

    List<RepairEvaluation> findByWorkerId(Long workerId);
}
