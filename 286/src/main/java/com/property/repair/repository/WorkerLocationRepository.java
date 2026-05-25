package com.property.repair.repository;

import com.property.repair.entity.WorkerLocation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface WorkerLocationRepository extends JpaRepository<WorkerLocation, Long> {

    Optional<WorkerLocation> findTopByWorkerIdOrderByCreateTimeDesc(Long workerId);

    @Query("SELECT w FROM WorkerLocation w WHERE w.workerId = :workerId AND w.createTime >= :startTime ORDER BY w.createTime ASC")
    List<WorkerLocation> findLocationHistory(Long workerId, LocalDateTime startTime);

    @Query("SELECT w FROM WorkerLocation w WHERE w.createTime >= :startTime")
    List<WorkerLocation> findRecentLocations(LocalDateTime startTime);
}
