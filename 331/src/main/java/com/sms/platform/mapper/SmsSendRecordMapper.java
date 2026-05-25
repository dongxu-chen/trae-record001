package com.sms.platform.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.sms.platform.entity.SmsSendRecord;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import java.time.LocalDateTime;
import java.util.Map;

@Mapper
public interface SmsSendRecordMapper extends BaseMapper<SmsSendRecord> {

    @Select("SELECT " +
            "COUNT(*) AS total, " +
            "SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS successCount, " +
            "SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS failCount, " +
            "SUM(CASE WHEN status = 3 THEN 1 ELSE 0 END) AS blacklistCount, " +
            "SUM(CASE WHEN status = 4 THEN 1 ELSE 0 END) AS rateLimitCount " +
            "FROM sms_send_record " +
            "WHERE create_time BETWEEN #{startTime} AND #{endTime} " +
            "AND deleted = 0")
    Map<String, Object> selectStatistics(@Param("startTime") LocalDateTime startTime, @Param("endTime") LocalDateTime endTime);

    @Select("SELECT " +
            "sms_type, " +
            "COUNT(*) AS total, " +
            "SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS successCount " +
            "FROM sms_send_record " +
            "WHERE create_time BETWEEN #{startTime} AND #{endTime} " +
            "AND deleted = 0 " +
            "GROUP BY sms_type")
    java.util.List<Map<String, Object>> selectStatisticsByType(@Param("startTime") LocalDateTime startTime, @Param("endTime") LocalDateTime endTime);

    @Select("SELECT " +
            "channel_code, " +
            "COUNT(*) AS total, " +
            "SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS successCount " +
            "FROM sms_send_record " +
            "WHERE create_time BETWEEN #{startTime} AND #{endTime} " +
            "AND deleted = 0 " +
            "GROUP BY channel_code")
    java.util.List<Map<String, Object>> selectStatisticsByChannel(@Param("startTime") LocalDateTime startTime, @Param("endTime") LocalDateTime endTime);
}
