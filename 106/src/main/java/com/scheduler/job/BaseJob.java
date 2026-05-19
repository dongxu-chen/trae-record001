package com.scheduler.job;

import com.scheduler.service.JobExecuteRecordService;
import org.quartz.DisallowConcurrentExecution;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.io.PrintWriter;
import java.io.StringWriter;

@Component
@DisallowConcurrentExecution
public abstract class BaseJob implements Job {

    @Resource
    private JobExecuteRecordService jobExecuteRecordService;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        String jobName = context.getJobDetail().getKey().getName();
        String jobGroup = context.getJobDetail().getKey().getGroup();
        long startTime = System.currentTimeMillis();
        boolean success = true;
        String result = null;
        String errorMessage = null;

        try {
            result = executeInternal(context);
        } catch (Exception e) {
            success = false;
            errorMessage = getStackTrace(e);
            throw new JobExecutionException(e);
        } finally {
            long duration = System.currentTimeMillis() - startTime;
            jobExecuteRecordService.saveRecord(jobName, jobGroup, success, result, errorMessage, duration);
        }
    }

    private String getStackTrace(Exception e) {
        StringWriter sw = new StringWriter();
        PrintWriter pw = new PrintWriter(sw);
        e.printStackTrace(pw);
        return sw.toString();
    }

    protected abstract String executeInternal(JobExecutionContext context) throws Exception;

}
