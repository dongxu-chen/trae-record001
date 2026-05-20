package com.scheduler.controller;

import com.scheduler.common.Result;
import com.scheduler.entity.JobExecuteRecord;
import com.scheduler.service.JobExecuteRecordService;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;

@RestController
@RequestMapping("/api/job/record")
public class JobExecuteRecordController {

    @Resource
    private JobExecuteRecordService jobExecuteRecordService;

    @GetMapping("/list")
    public Result<Page<JobExecuteRecord>> getRecords(
            @RequestParam(required = false) String jobName,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            Page<JobExecuteRecord> records = jobExecuteRecordService.getRecords(jobName, page, size);
            return Result.success(records);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

}
