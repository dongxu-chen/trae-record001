package com.sms.platform.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.sms.platform.entity.SmsMobileLocation;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Mapper
public interface SmsMobileLocationMapper extends BaseMapper<SmsMobileLocation> {

    @Select("SELECT " +
            "sr.mobile_province AS province, " +
            "COUNT(*) AS total, " +
            "SUM(CASE WHEN sr.status = 1 THEN 1 ELSE 0 END) AS successCount " +
            "FROM sms_send_record sr " +
            "WHERE sr.create_time BETWEEN #{startTime} AND #{endTime} " +
            "AND sr.deleted = 0 " +
            "AND sr.mobile_province IS NOT NULL " +
            "GROUP BY sr.mobile_province " +
            "ORDER BY total DESC")
    List<Map<String, Object>> selectStatisticsByProvince(@Param("startTime") LocalDateTime startTime, @Param("endTime") LocalDateTime endTime);

    @Select("SELECT " +
            "sr.mobile_operator AS operator, " +
            "COUNT(*) AS total, " +
            "SUM(CASE WHEN sr.status = 1 THEN 1 ELSE 0 END) AS successCount " +
            "FROM sms_send_record sr " +
            "WHERE sr.create_time BETWEEN #{startTime} AND #{endTime} " +
            "AND sr.deleted = 0 " +
            "AND sr.mobile_operator IS NOT NULL " +
            "GROUP BY sr.mobile_operator " +
            "ORDER BY total DESC")
    List<Map<String, Object>> selectStatisticsByOperator(@Param("startTime") LocalDateTime startTime, @Param("endTime") LocalDateTime endTime);
}
