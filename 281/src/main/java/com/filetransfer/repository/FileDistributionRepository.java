package com.filetransfer.repository;

import com.filetransfer.entity.FileDistribution;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileDistributionRepository extends JpaRepository<FileDistribution, Long> {
    Optional<FileDistribution> findByDistributionId(String distributionId);
    List<FileDistribution> findBySourceUserIdOrderByCreatedAtDesc(Long sourceUserId);
}
