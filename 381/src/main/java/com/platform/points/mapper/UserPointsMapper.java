package com.platform.points.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.platform.points.entity.UserPoints;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface UserPointsMapper extends BaseMapper<UserPoints> {

    @Update("UPDATE user_points SET available_points = available_points + #{points}, total_points = total_points + #{points}, " +
            "version = version + 1, update_time = NOW() WHERE user_id = #{userId} AND deleted = 0")
    int addPoints(@Param("userId") Long userId, @Param("points") Integer points);

    @Update("UPDATE user_points SET available_points = available_points - #{points}, " +
            "version = version + 1, update_time = NOW() WHERE user_id = #{userId} AND available_points >= #{points} AND deleted = 0")
    int deductPoints(@Param("userId") Long userId, @Param("points") Integer points);
}
