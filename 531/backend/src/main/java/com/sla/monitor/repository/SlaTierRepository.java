package com.sla.monitor.repository;

import com.sla.monitor.model.SlaTier;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SlaTierRepository extends JpaRepository<SlaTier, Long> {

    Optional<SlaTier> findByTierCode(String tierCode);

    Optional<SlaTier> findByTierName(String tierName);

    List<SlaTier> findByActiveTrue();

    List<SlaTier> findByActiveTrueOrderByPriorityLevelAsc();

    boolean existsByTierCode(String tierCode);

    boolean existsByTierName(String tierName);
}
