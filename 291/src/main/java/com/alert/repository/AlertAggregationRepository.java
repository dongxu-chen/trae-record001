package com.alert.repository;

import com.alert.entity.AlertAggregation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface AlertAggregationRepository extends JpaRepository<AlertAggregation, Long> {

    Optional<AlertAggregation> findByAggregationKey(String aggregationKey);

    Optional<AlertAggregation> findByAggregationKeyAndStatus(String aggregationKey, String status);
}
