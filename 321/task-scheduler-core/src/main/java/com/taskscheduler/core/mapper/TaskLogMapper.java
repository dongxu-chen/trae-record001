package com.taskscheduler.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.taskscheduler.common.entity.TaskLog;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskLogMapper extends BaseMapper<TaskLog> {
}
