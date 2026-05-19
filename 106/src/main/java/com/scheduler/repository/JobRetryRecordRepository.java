package com.scheduler.repository;

import com.scheduler.entity.JobRetryRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface JobRetryRecordRepository extends JpaRepository<JobRetryRecord, Long> {

    Optional<JobRetryRecord> findFirstByJobNameAndJobGroupOrderByFireTimeDesc(String jobName, String jobGroup);

    void deleteByJobNameAndJobGroup(String jobName, String jobGroup);

}
