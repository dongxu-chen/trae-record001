package com.taskscheduler.common.handler;

import com.taskscheduler.common.dto.TaskExecuteParam;
import com.taskscheduler.common.dto.TaskExecuteResult;

public interface ITaskHandler {

    TaskExecuteResult execute(TaskExecuteParam param) throws Exception;
}
