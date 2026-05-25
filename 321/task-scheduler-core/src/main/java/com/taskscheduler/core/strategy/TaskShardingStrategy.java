package com.taskscheduler.core.strategy;

import com.alibaba.fastjson2.TypeReference;
import com.taskscheduler.common.dto.TaskExecuteParam;
import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.entity.TaskShard;
import com.taskscheduler.common.util.JsonUtils;
import com.taskscheduler.core.mapper.TaskShardMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class TaskShardingStrategy {

    @Autowired
    private TaskShardMapper taskShardMapper;

    public List<TaskExecuteParam> createShardingParams(TaskInfo taskInfo, Long logId) {
        List<TaskExecuteParam> params = new ArrayList<>();
        int shardingTotal = taskInfo.getShardingTotal() != null ? taskInfo.getShardingTotal() : 1;

        if (shardingTotal <= 1) {
            TaskExecuteParam param = buildExecuteParam(taskInfo, logId, -1, 1, null);
            params.add(param);
            return params;
        }

        List<String> shardParams = parseShardingParams(taskInfo.getShardingParam(), shardingTotal);

        for (int i = 0; i < shardingTotal; i++) {
            String shardParam = i < shardParams.size() ? shardParams.get(i) : null;
            TaskExecuteParam param = buildExecuteParam(taskInfo, logId, i, shardingTotal, shardParam);
            params.add(param);

            TaskShard taskShard = new TaskShard();
            taskShard.setTaskId(taskInfo.getId());
            taskShard.setLogId(logId);
            taskShard.setShardIndex(i);
            taskShard.setShardTotal(shardingTotal);
            taskShard.setShardParam(shardParam);
            taskShard.setStatus(0);
            taskShard.setRetryCount(0);
            taskShardMapper.insert(taskShard);
        }

        return params;
    }

    private List<String> parseShardingParams(String shardingParamJson, int shardingTotal) {
        List<String> result = new ArrayList<>();
        if (shardingParamJson == null || shardingParamJson.trim().isEmpty()) {
            for (int i = 0; i < shardingTotal; i++) {
                result.add(String.valueOf(i));
            }
            return result;
        }

        try {
            Map<String, Object> config = JsonUtils.parseObject(shardingParamJson, new TypeReference<Map<String, Object>>() {});
            if (config != null && config.containsKey("params")) {
                Object paramsObj = config.get("params");
                if (paramsObj instanceof List) {
                    List<?> list = (List<?>) paramsObj;
                    for (Object obj : list) {
                        result.add(String.valueOf(obj));
                    }
                }
            }
        } catch (Exception e) {
            for (int i = 0; i < shardingTotal; i++) {
                result.add(String.valueOf(i));
            }
        }

        while (result.size() < shardingTotal) {
            result.add(String.valueOf(result.size()));
        }

        return result;
    }

    private TaskExecuteParam buildExecuteParam(TaskInfo taskInfo, Long logId,
                                                int shardingIndex, int shardingTotal, String shardingParam) {
        TaskExecuteParam param = new TaskExecuteParam();
        param.setTaskId(taskInfo.getId());
        param.setLogId(logId);
        param.setTaskName(taskInfo.getTaskName());
        param.setTaskGroup(taskInfo.getTaskGroup());
        param.setHandler(taskInfo.getHandler());
        param.setParams(taskInfo.getParams());
        param.setShardingIndex(shardingIndex);
        param.setShardingTotal(shardingTotal);
        param.setShardingParam(shardingParam);
        param.setTimeout(taskInfo.getTaskTimeout());
        param.setRetryCount(0);
        return param;
    }
}
