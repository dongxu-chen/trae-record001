package com.datatransfer.migration.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.datatransfer.migration.model.DataSource;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface DataSourceRepository extends BaseMapper<DataSource> {
}
