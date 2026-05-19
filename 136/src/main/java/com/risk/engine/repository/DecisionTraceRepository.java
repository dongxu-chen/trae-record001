package com.risk.engine.repository;

import com.risk.engine.entity.DecisionTrace;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface DecisionTraceRepository extends JpaRepository<DecisionTrace, Long> {

    List<DecisionTrace> findByRequestIdOrderByTraceTimeAsc(String requestId);

    List<DecisionTrace> findByUserId(String userId);

    Page<DecisionTrace> findByUserId(String userId, Pageable pageable);

    @Query("SELECT t FROM DecisionTrace t WHERE t.requestId = :requestId ORDER BY t.traceTime ASC")
    List<DecisionTrace> getFullTrace(@Param("requestId") String requestId);

    @Query("SELECT t FROM DecisionTrace t WHERE t.userId = :userId AND t.traceTime BETWEEN :startTime AND :endTime ORDER BY t.traceTime DESC")
    List<DecisionTrace> findByUserIdAndTimeRange(@Param("userId") String userId,
                                                  @Param("startTime") LocalDateTime startTime,
                                                  @Param("endTime") LocalDateTime endTime);

    @Query("SELECT t FROM DecisionTrace t WHERE t.step = :step AND t.traceTime BETWEEN :startTime AND :endTime ORDER BY t.traceTime DESC")
    List<DecisionTrace> findByStepAndTimeRange(@Param("step") String step,
                                                @Param("startTime") LocalDateTime startTime,
                                                @Param("endTime") LocalDateTime endTime);

    @Query("SELECT DISTINCT t.requestId FROM DecisionTrace t WHERE t.result = :result AND t.traceTime BETWEEN :startTime AND :endTime")
    List<String> findRequestIdsByResultAndTimeRange(@Param("result") String result,
                                                      @Param("startTime") LocalDateTime startTime,
                                                      @Param("endTime") LocalDateTime endTime);
}
