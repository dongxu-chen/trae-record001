package com.scheduler.service;

import com.scheduler.entity.JobExecuteRecord;
import com.scheduler.repository.JobExecuteRecordRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.LocalDateTime;

@Service
public class JobExecuteRecordService {

    @Resource
    private JobExecuteRecordRepository jobExecuteRecordRepository;

    public void saveRecord(String jobName, String jobGroup, boolean success, String result, String errorMessage, long durationMs) {
        JobExecuteRecord record = new JobExecuteRecord();
        record.setJobName(jobName);
        record.setJobGroup(jobGroup);
        record.setExecuteTime(LocalDateTime.now());
        record.setExecuteStatus(success ? "SUCCESS" : "FAILED");
        record.setExecuteResult(result);
        record.setErrorMessage(errorMessage);
        record.setDurationMs(durationMs);
        jobExecuteRecordRepository.save(record);
    }

    public Page<JobExecuteRecord> getRecords(String jobName, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        if (jobName != null && !jobName.isEmpty()) {
            return jobExecuteRecordRepository.findByJobNameOrderByExecuteTimeDesc(jobName, pageable);
        }
        return jobExecuteRecordRepository.findAllByOrderByExecuteTimeDesc(pageable);
    }

}
