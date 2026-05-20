package com.risk.engine.repository;

import com.risk.engine.entity.FeatureSnapshot;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface FeatureSnapshotRepository extends JpaRepository<FeatureSnapshot, Long> {

    Optional<FeatureSnapshot> findByRequestId(String requestId);

    List<FeatureSnapshot> findByUserId(String userId);

    Page<FeatureSnapshot> findByUserId(String userId, Pageable pageable);

    List<FeatureSnapshot> findByScene(String scene);

    @Query("SELECT f FROM FeatureSnapshot f WHERE f.userId = :userId AND f.createTime BETWEEN :startTime AND :endTime ORDER BY f.createTime DESC")
    List<FeatureSnapshot> findByUserIdAndTimeRange(@Param("userId") String userId,
                                                     @Param("startTime") LocalDateTime startTime,
                                                     @Param("endTime") LocalDateTime endTime);

    @Query("SELECT f FROM FeatureSnapshot f WHERE f.scene = :scene AND f.decision = :decision ORDER BY f.createTime DESC")
    Page<FeatureSnapshot> findBySceneAndDecision(@Param("scene") String scene,
                                                   @Param("decision") String decision,
                                                   Pageable pageable);

    @Query("SELECT f FROM FeatureSnapshot f WHERE f.createTime BETWEEN :startTime AND :endTime ORDER BY f.createTime DESC")
    List<FeatureSnapshot> findByTimeRange(@Param("startTime") LocalDateTime startTime,
                                           @Param("endTime") LocalDateTime endTime);

    @Query(value = "SELECT * FROM t_feature_snapshot ORDER BY create_time DESC LIMIT :limit", nativeQuery = true)
    List<FeatureSnapshot> findRecentSnapshots(@Param("limit") int limit);
}
