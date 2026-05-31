package com.depguard.repository;

import com.depguard.entity.ScanResult;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ScanResultRepository extends JpaRepository<ScanResult, Long> {
    List<ScanResult> findByRepoId(Long repoId);
}
