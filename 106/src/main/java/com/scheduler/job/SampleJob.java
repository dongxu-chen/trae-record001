package com.scheduler.job;

import org.quartz.JobExecutionContext;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Component
public class SampleJob extends BaseJob {

    @Override
    protected String executeInternal(JobExecutionContext context) throws Exception {
        String currentTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        System.out.println("SampleJob 执行时间: " + currentTime);
        
        Thread.sleep(1000);
        
        return "执行成功，时间: " + currentTime;
    }

}
