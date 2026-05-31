package com.flink.recommender.repository;

import com.flink.recommender.model.ResourceConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ResourceConfigRepository extends JpaRepository<ResourceConfig, Long> {

    Optional<ResourceConfig> findByJobId(String jobId);

    List<ResourceConfig> findByJobNameContainingIgnoreCase(String jobName);

    List<ResourceConfig> findAllByOrderByCreatedAtDesc();

    List<ResourceConfig> findTop10ByOrderByCreatedAtDesc();
}
