package com.scheduler.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.util.List;

@Data
public class JobDTO {

    @NotBlank(message = "任务名称不能为空")
    private String jobName;

    private String jobGroup = "DEFAULT";

    @NotBlank(message = "Cron表达式不能为空")
    private String cronExpression;

    @NotBlank(message = "执行类名不能为空")
    private String jobClassName;

    private String description;

    private Integer retryCount = 0;

    private Integer retryInterval = 30000;

    private Integer timeoutSeconds = 300;

    private List<String> dependsOn;

}
