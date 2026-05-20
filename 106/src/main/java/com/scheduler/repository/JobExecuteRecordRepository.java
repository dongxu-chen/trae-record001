package com.scheduler.repository;

import com.scheduler.entity.JobExecuteRecord;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface JobExecuteRecordRepository extends JpaRepository<JobExecuteRecord, Long> {

    Page<JobExecuteRecord> findByJobNameOrderByExecuteTimeDesc(String jobName, Pageable pageable);

    Page<JobExecuteRecord> findAllByOrderByExecuteTimeDesc(Pageable pageable);

    Optional<JobExecuteRecord> findFirstByJobNameAndJobGroupOrderByExecuteTimeDesc(String jobName, String jobGroup);

}
