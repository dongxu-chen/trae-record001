package com.platform.points.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.platform.points.dto.PointsRecordQueryDTO;
import com.platform.points.entity.PointsRecord;
import com.platform.points.vo.PointsRecordVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface PointsRecordMapper extends BaseMapper<PointsRecord> {

    IPage<PointsRecordVO> selectRecordPage(Page<PointsRecordVO> page, @Param("query") PointsRecordQueryDTO query);
}
