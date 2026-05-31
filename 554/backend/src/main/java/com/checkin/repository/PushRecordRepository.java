package com.checkin.repository;

import com.checkin.entity.PushRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface PushRecordRepository extends JpaRepository<PushRecord, Long> {
    List<PushRecord> findByUserIdOrderByCreateTimeDesc(Long userId);
    List<PushRecord> findByCreateTimeBetween(LocalDateTime startTime, LocalDateTime endTime);
    List<PushRecord> findByUserIdAndPushTypeAndCreateTimeBetween(
            Long userId, String pushType, LocalDateTime startTime, LocalDateTime endTime);
}
