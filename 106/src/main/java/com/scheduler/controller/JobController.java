package com.scheduler.controller;

import com.scheduler.common.Result;
import com.scheduler.dto.JobDTO;
import com.scheduler.dto.JobDependencyGraph;
import com.scheduler.service.JobService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/job")
public class JobController {

    @Resource
    private JobService jobService;

    @PostMapping
    public Result<Void> addJob(@Validated @RequestBody JobDTO jobDTO) {
        try {
            jobService.addJob(jobDTO);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PutMapping
    public Result<Void> updateJob(@Validated @RequestBody JobDTO jobDTO) {
        try {
            jobService.updateJob(jobDTO);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping
    public Result<Void> deleteJob(@RequestParam String jobName,
                                   @RequestParam(defaultValue = "DEFAULT") String jobGroup) {
        try {
            jobService.deleteJob(jobName, jobGroup);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/pause")
    public Result<Void> pauseJob(@RequestParam String jobName,
                                  @RequestParam(defaultValue = "DEFAULT") String jobGroup) {
        try {
            jobService.pauseJob(jobName, jobGroup);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/resume")
    public Result<Void> resumeJob(@RequestParam String jobName,
                                   @RequestParam(defaultValue = "DEFAULT") String jobGroup) {
        try {
            jobService.resumeJob(jobName, jobGroup);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/trigger")
    public Result<Void> triggerJob(@RequestParam String jobName,
                                    @RequestParam(defaultValue = "DEFAULT") String jobGroup) {
        try {
            jobService.triggerJob(jobName, jobGroup);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping
    public Result<Map<String, Object>> getJob(@RequestParam String jobName,
                                               @RequestParam(defaultValue = "DEFAULT") String jobGroup) {
        try {
            Map<String, Object> job = jobService.getJob(jobName, jobGroup);
            return Result.success(job);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/list")
    public Result<List<Map<String, Object>>> getAllJobs() {
        try {
            List<Map<String, Object>> jobs = jobService.getAllJobs();
            return Result.success(jobs);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/dependency-graph")
    public Result<JobDependencyGraph> getDependencyGraph() {
        try {
            JobDependencyGraph graph = jobService.getDependencyGraph();
            return Result.success(graph);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

}
