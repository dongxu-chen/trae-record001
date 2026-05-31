package com.depguard.repository;

import com.depguard.entity.UpgradeSuggestionRecord;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface UpgradeSuggestionRecordRepository extends JpaRepository<UpgradeSuggestionRecord, Long> {
    List<UpgradeSuggestionRecord> findByRepoId(Long repoId);
}
