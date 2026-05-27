package com.platform.points.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.platform.points.entity.PointsLevelConfig;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface PointsLevelConfigMapper extends BaseMapper<PointsLevelConfig> {

    @Select("SELECT * FROM points_level_config WHERE status = 1 AND deleted = 0 ORDER BY level_order ASC")
    List<PointsLevelConfig> selectAllActiveLevels();

    @Select("SELECT * FROM points_level_config WHERE min_points <= #{points} AND max_points > #{points} " +
            "AND status = 1 AND deleted = 0 LIMIT 1")
    PointsLevelConfig selectLevelByPoints(Integer points);

    @Select("SELECT * FROM points_level_config WHERE level_order > #{currentLevelOrder} AND status = 1 AND deleted = 0 " +
            "ORDER BY level_order ASC LIMIT 1")
    PointsLevelConfig selectNextLevel(Integer currentLevelOrder);
}
