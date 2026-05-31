package com.flink.recommender.repository;

import com.flink.recommender.model.JobHistoryRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface JobHistoryRepository extends JpaRepository<JobHistoryRecord, Long> {

    List<JobHistoryRecord> findByJobIdOrderByRecordedAtDesc(String jobId);

    List<JobHistoryRecord> findTop10ByJobIdOrderByRecordedAtDesc(String jobId);

    List<JobHistoryRecord> findByJobIdAndRecordedAtAfterOrderByRecordedAtDesc(
            String jobId, LocalDateTime after);

    Optional<JobHistoryRecord> findFirstByJobIdOrderByRecordedAtDesc(String jobId);

    List<JobHistoryRecord> findByJobNameOrderByRecordedAtDesc(String jobName);

    long countByJobId(String jobId);
}
