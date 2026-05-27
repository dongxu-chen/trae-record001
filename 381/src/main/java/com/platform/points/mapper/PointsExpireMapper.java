package com.platform.points.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.platform.points.entity.PointsExpire;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface PointsExpireMapper extends BaseMapper<PointsExpire> {

    @Select("SELECT * FROM points_expire WHERE user_id = #{userId} AND remaining_points > 0 AND status = 0 " +
            "AND expire_time <= NOW() AND deleted = 0 ORDER BY create_time ASC")
    List<PointsExpire> selectExpiredByUserId(@Param("userId") Long userId);

    @Select("SELECT * FROM points_expire WHERE id > #{lastId} AND remaining_points > 0 AND status = 0 " +
            "AND expire_time <= #{now} AND deleted = 0 ORDER BY id ASC LIMIT #{limit}")
    List<PointsExpire> selectBatchExpired(@Param("lastId") Long lastId, @Param("now") LocalDateTime now, @Param("limit") int limit);

    @Select("SELECT MAX(id) FROM points_expire WHERE deleted = 0")
    Long selectMaxId();

    @Update("UPDATE points_expire SET remaining_points = remaining_points - #{points}, " +
            "status = CASE WHEN remaining_points - #{points} = 0 THEN 1 ELSE status END, " +
            "update_time = NOW() WHERE id = #{id} AND remaining_points >= #{points} AND deleted = 0")
    int consumePoints(@Param("id") Long id, @Param("points") Integer points);

    @Update("UPDATE points_expire SET status = 1, update_time = NOW() WHERE id = #{id} AND deleted = 0")
    int markExpired(@Param("id") Long id);
}
