package com.property.repair.repository;

import com.property.repair.entity.RepairWorker;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RepairWorkerRepository extends JpaRepository<RepairWorker, Long> {

    RepairWorker findByWorkerId(Long workerId);

    List<RepairWorker> findByStatus(Integer status);
}
