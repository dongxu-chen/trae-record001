package com.taskscheduler.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.taskscheduler.common.entity.TaskInfo;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskInfoMapper extends BaseMapper<TaskInfo> {
}
