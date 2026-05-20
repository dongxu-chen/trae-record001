package com.scheduler.service;

import com.scheduler.dto.JobDTO;
import com.scheduler.dto.JobDependencyGraph;
import com.scheduler.entity.JobConfig;
import com.scheduler.repository.JobConfigRepository;
import com.scheduler.util.QuartzManager;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.quartz.*;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class JobService {

    @Resource
    private QuartzManager quartzManager;

    @Resource
    private Scheduler scheduler;

    @Resource
    private JobConfigRepository jobConfigRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    public void addJob(JobDTO jobDTO) throws Exception {
        if (quartzManager.checkJobExists(jobDTO.getJobName(), jobDTO.getJobGroup())) {
            throw new Exception("任务已存在");
        }
        quartzManager.addJob(jobDTO);
    }

    public void updateJob(JobDTO jobDTO) throws Exception {
        if (!quartzManager.checkJobExists(jobDTO.getJobName(), jobDTO.getJobGroup())) {
            throw new Exception("任务不存在");
        }
        quartzManager.updateJob(jobDTO);
    }

    public void deleteJob(String jobName, String jobGroup) throws Exception {
        if (!quartzManager.checkJobExists(jobName, jobGroup)) {
            throw new Exception("任务不存在");
        }
        quartzManager.deleteJob(jobName, jobGroup);
    }

    public void pauseJob(String jobName, String jobGroup) throws Exception {
        if (!quartzManager.checkJobExists(jobName, jobGroup)) {
            throw new Exception("任务不存在");
        }
        quartzManager.pauseJob(jobName, jobGroup);
    }

    public void resumeJob(String jobName, String jobGroup) throws Exception {
        if (!quartzManager.checkJobExists(jobName, jobGroup)) {
            throw new Exception("任务不存在");
        }
        quartzManager.resumeJob(jobName, jobGroup);
    }

    public void triggerJob(String jobName, String jobGroup) throws Exception {
        if (!quartzManager.checkJobExists(jobName, jobGroup)) {
            throw new Exception("任务不存在");
        }
        quartzManager.triggerJob(jobName, jobGroup);
    }

    public Map<String, Object> getJob(String jobName, String jobGroup) throws Exception {
        JobKey jobKey = JobKey.jobKey(jobName, jobGroup);
        JobDetail jobDetail = scheduler.getJobDetail(jobKey);
        if (jobDetail == null) {
            return null;
        }

        TriggerKey triggerKey = TriggerKey.triggerKey(jobName, jobGroup);
        CronTrigger trigger = (CronTrigger) scheduler.getTrigger(triggerKey);
        Trigger.TriggerState state = quartzManager.getJobState(jobName, jobGroup);

        JobConfig config = jobConfigRepository.findByJobNameAndJobGroup(jobName, jobGroup).orElse(null);

        Map<String, Object> jobMap = new HashMap<>();
        jobMap.put("jobName", jobDetail.getKey().getName());
        jobMap.put("jobGroup", jobDetail.getKey().getGroup());
        jobMap.put("description", jobDetail.getDescription());
        jobMap.put("jobClassName", jobDetail.getJobClass().getName());
        jobMap.put("cronExpression", trigger != null ? trigger.getCronExpression() : "");
        jobMap.put("state", state.name());
        jobMap.put("nextFireTime", trigger != null ? trigger.getNextFireTime() : null);
        jobMap.put("previousFireTime", trigger != null ? trigger.getPreviousFireTime() : null);

        if (config != null) {
            jobMap.put("retryCount", config.getRetryCount());
            jobMap.put("retryInterval", config.getRetryInterval());
            jobMap.put("timeoutSeconds", config.getTimeoutSeconds());
            if (config.getDependsOn() != null) {
                jobMap.put("dependsOn", objectMapper.readValue(config.getDependsOn(),
                        new TypeReference<List<String>>() {}));
            }
        }

        return jobMap;
    }

    public List<Map<String, Object>> getAllJobs() throws Exception {
        List<Map<String, Object>> jobList = new ArrayList<>();

        for (String groupName : scheduler.getJobGroupNames()) {
            for (JobKey jobKey : scheduler.getJobKeys(JobGroupMatcher.jobGroupEquals(groupName))) {
                JobDetail jobDetail = scheduler.getJobDetail(jobKey);
                TriggerKey triggerKey = TriggerKey.triggerKey(jobKey.getName(), jobKey.getGroup());
                CronTrigger trigger = (CronTrigger) scheduler.getTrigger(triggerKey);
                Trigger.TriggerState state = scheduler.getTriggerState(triggerKey);
                JobConfig config = jobConfigRepository.findByJobNameAndJobGroup(jobKey.getName(), jobKey.getGroup()).orElse(null);

                Map<String, Object> jobMap = new HashMap<>();
                jobMap.put("jobName", jobKey.getName());
                jobMap.put("jobGroup", jobKey.getGroup());
                jobMap.put("description", jobDetail.getDescription());
                jobMap.put("jobClassName", jobDetail.getJobClass().getName());
                jobMap.put("cronExpression", trigger != null ? trigger.getCronExpression() : "");
                jobMap.put("state", state.name());
                jobMap.put("nextFireTime", trigger != null ? trigger.getNextFireTime() : null);
                jobMap.put("previousFireTime", trigger != null ? trigger.getPreviousFireTime() : null);

                if (config != null) {
                    jobMap.put("retryCount", config.getRetryCount());
                    jobMap.put("retryInterval", config.getRetryInterval());
                    jobMap.put("timeoutSeconds", config.getTimeoutSeconds());
                    if (config.getDependsOn() != null) {
                        jobMap.put("dependsOn", objectMapper.readValue(config.getDependsOn(),
                                new TypeReference<List<String>>() {}));
                    }
                }

                jobList.add(jobMap);
            }
        }

        return jobList;
    }

    public JobDependencyGraph getDependencyGraph() throws Exception {
        JobDependencyGraph graph = new JobDependencyGraph();
        Map<String, JobDependencyGraph.Node> nodeMap = new HashMap<>();

        List<Map<String, Object>> allJobs = getAllJobs();

        for (Map<String, Object> job : allJobs) {
            String jobId = job.get("jobGroup") + ":" + job.get("jobName");

            JobDependencyGraph.Node node = new JobDependencyGraph.Node();
            node.setId(jobId);
            node.setName((String) job.get("jobName"));
            node.setGroup((String) job.get("jobGroup"));
            node.setStatus((String) job.get("state"));
            node.setCronExpression((String) job.get("cronExpression"));
            node.setDescription((String) job.get("description"));
            node.setRetryCount((Integer) job.get("retryCount"));
            node.setTimeoutSeconds((Integer) job.get("timeoutSeconds"));

            graph.getNodes().add(node);
            nodeMap.put(jobId, node);

            @SuppressWarnings("unchecked")
            List<String> dependsOn = (List<String>) job.get("dependsOn");
            if (dependsOn != null) {
                for (String dep : dependsOn) {
                    String[] parts = dep.split(":");
                    String depName = parts[0];
                    String depGroup = parts.length > 1 ? parts[1] : "DEFAULT";
                    String depId = depGroup + ":" + depName;

                    JobDependencyGraph.Edge edge = new JobDependencyGraph.Edge();
                    edge.setSource(depId);
                    edge.setTarget(jobId);
                    edge.setLabel("depends on");
                    graph.getEdges().add(edge);
                }
            }
        }

        return graph;
    }

}
