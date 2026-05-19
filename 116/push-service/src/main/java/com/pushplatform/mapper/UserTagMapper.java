package com.pushplatform.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.pushplatform.entity.UserTag;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface UserTagMapper extends BaseMapper<UserTag> {

    @Select("SELECT DISTINCT user_id FROM user_tag WHERE tag_code = #{tagCode} AND deleted = 0")
    List<String> selectUserIdsByTagCode(@Param("tagCode") String tagCode);
}
