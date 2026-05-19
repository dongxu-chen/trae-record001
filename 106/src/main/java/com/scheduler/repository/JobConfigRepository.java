package com.scheduler.repository;

import com.scheduler.entity.JobConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface JobConfigRepository extends JpaRepository<JobConfig, Long> {

    Optional<JobConfig> findByJobNameAndJobGroup(String jobName, String jobGroup);

    List<JobConfig> findByJobGroup(String jobGroup);

    void deleteByJobNameAndJobGroup(String jobName, String jobGroup);

}
