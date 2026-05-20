package com.risk.engine.repository;

import com.risk.engine.entity.RiskList;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface RiskListRepository extends JpaRepository<RiskList, Long> {

    List<RiskList> findByListTypeAndStatusAndFieldName(String listType, String status, String fieldName);

    @Query("SELECT r FROM RiskList r WHERE r.status = 'ENABLED' " +
           "AND (r.expireTime IS NULL OR r.expireTime > :now)")
    List<RiskList> findAllActiveLists(@Param("now") LocalDateTime now);

    @Query("SELECT r FROM RiskList r WHERE r.listType = :listType " +
           "AND r.status = 'ENABLED' " +
           "AND (r.expireTime IS NULL OR r.expireTime > :now)")
    List<RiskList> findActiveListsByType(@Param("listType") String listType, @Param("now") LocalDateTime now);
}
