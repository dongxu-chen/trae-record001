package com.wolfkill.repository;

import com.wolfkill.entity.GameRecord;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface GameRecordRepository extends JpaRepository<GameRecord, Long> {
    Page<GameRecord> findAllByOrderByCreatedAtDesc(Pageable pageable);
}
