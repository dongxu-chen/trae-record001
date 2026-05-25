package com.filetransfer.repository;

import com.filetransfer.entity.DistributionFile;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DistributionFileRepository extends JpaRepository<DistributionFile, Long> {
    List<DistributionFile> findByDistributionIdOrderByCreatedAtDesc(String distributionId);
}
