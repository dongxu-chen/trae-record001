package com.apiversion.version.mapper;

import com.apiversion.version.entity.HeaderParseRule;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface HeaderParseRuleMapper extends BaseMapper<HeaderParseRule> {

    @Select("SELECT * FROM header_parse_rule WHERE routing_rule_id = #{routingRuleId} AND deleted = 0 ORDER BY priority ASC")
    List<HeaderParseRule> selectByRoutingRuleId(@Param("routingRuleId") Long routingRuleId);

    @Select("SELECT * FROM header_parse_rule WHERE deleted = 0 ORDER BY priority ASC")
    List<HeaderParseRule> selectAllEnabled();
}
