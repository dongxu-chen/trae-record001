package com.configcenter.server.repository;

import com.configcenter.server.entity.ConfigSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface ConfigSnapshotRepository extends JpaRepository<ConfigSnapshot, Long> {

    List<ConfigSnapshot> findByApplicationOrderBySnapshotTimeDesc(String application);

    List<ConfigSnapshot> findByApplicationAndProfileAndLabelOrderBySnapshotTimeDesc(
            String application, String profile, String label);

    @Query("SELECT s FROM ConfigSnapshot s WHERE s.application = :application " +
            "AND s.profile = :profile AND s.label = :label " +
            "AND s.snapshotTime <= :targetTime " +
            "ORDER BY s.snapshotTime DESC")
    List<ConfigSnapshot> findLatestSnapshotBeforeTime(
            @Param("application") String application,
            @Param("profile") String profile,
            @Param("label") String label,
            @Param("targetTime") LocalDateTime targetTime);

    @Query("SELECT s FROM ConfigSnapshot s WHERE s.application = :application " +
            "AND s.profile = :profile AND s.label = :label " +
            "AND s.snapshotTime BETWEEN :startTime AND :endTime " +
            "ORDER BY s.snapshotTime DESC")
    List<ConfigSnapshot> findSnapshotsInTimeRange(
            @Param("application") String application,
            @Param("profile") String profile,
            @Param("label") String label,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime);

    Optional<ConfigSnapshot> findByApplicationAndProfileAndLabelAndVersion(
            String application, String profile, String label, String version);
}
