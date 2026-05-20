package com.scheduler.job;

import org.quartz.JobExecutionContext;
import org.springframework.stereotype.Component;

@Component
public class TestErrorJob extends BaseJob {

    @Override
    protected String executeInternal(JobExecutionContext context) throws Exception {
        System.out.println("TestErrorJob 开始执行...");
        
        int a = 1;
        int b = 0;
        int result = a / b;
        
        return "执行成功，结果: " + result;
    }

}
