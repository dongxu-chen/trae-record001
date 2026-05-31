package com.depguard.repository;

import com.depguard.entity.DependencyRecord;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DependencyRecordRepository extends JpaRepository<DependencyRecord, Long> {
    List<DependencyRecord> findByScanId(Long scanId);
    List<DependencyRecord> findByGroupIdAndArtifactId(String groupId, String artifactId);
}
