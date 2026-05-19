package com.pushplatform.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.pushplatform.entity.PushRecord;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface PushRecordMapper extends BaseMapper<PushRecord> {
}
