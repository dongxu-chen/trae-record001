package com.taskscheduler.executor.handler;

import com.taskscheduler.common.dto.TaskExecuteParam;
import com.taskscheduler.common.dto.TaskExecuteResult;
import com.taskscheduler.common.handler.ITaskHandler;
import com.taskscheduler.common.util.JsonUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;

@Slf4j
@Component("demoTask")
public class DemoTaskHandler implements ITaskHandler {

    @Override
    public TaskExecuteResult execute(TaskExecuteParam param) throws Exception {
        log.info("DemoTask execute start, taskId: {}, logId: {}, shard: {}/{}",
                param.getTaskId(), param.getLogId(), param.getShardingIndex(), param.getShardingTotal());

        LocalDateTime startTime = LocalDateTime.now();

        try {
            Thread.sleep(1000);

            StringBuilder result = new StringBuilder();
            result.append("DemoTask执行成功! ");
            result.append("任务ID: ").append(param.getTaskId()).append(", ");
            result.append("日志ID: ").append(param.getLogId()).append(", ");

            if (param.getShardingIndex() != null && param.getShardingIndex() >= 0) {
                result.append("分片: ").append(param.getShardingIndex())
                        .append("/").append(param.getShardingTotal()).append(", ");
                if (param.getShardingParam() != null) {
                    result.append("分片参数: ").append(param.getShardingParam()).append(", ");
                }
            }

            if (param.getParams() != null && !param.getParams().trim().isEmpty()) {
                try {
                    Map<String, Object> params = JsonUtils.parseObject(param.getParams(),
                            new com.alibaba.fastjson2.TypeReference<Map<String, Object>>() {});
                    result.append("业务参数: ").append(params);
                } catch (Exception e) {
                    result.append("原始参数: ").append(param.getParams());
                }
            }

            log.info("DemoTask execute success: {}", result);

            TaskExecuteResult executeResult = new TaskExecuteResult();
            executeResult.setLogId(param.getLogId());
            executeResult.setExecuteCode(0);
            executeResult.setExecuteMsg(result.toString());
            executeResult.setExecuteStartTime(startTime);
            executeResult.setExecuteEndTime(LocalDateTime.now());
            executeResult.setShardingIndex(param.getShardingIndex());
            return executeResult;

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw e;
        }
    }
}
