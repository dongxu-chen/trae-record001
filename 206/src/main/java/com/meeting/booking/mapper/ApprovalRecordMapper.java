package com.meeting.booking.mapper;

import com.meeting.booking.entity.ApprovalRecord;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface ApprovalRecordMapper {

    ApprovalRecord selectById(@Param("id") Long id);

    List<ApprovalRecord> selectByBookingId(@Param("bookingId") Long bookingId);

    List<ApprovalRecord> selectByApproverId(@Param("approverId") Long approverId, @Param("status") Integer status);

    List<ApprovalRecord> selectPendingApprovals();

    int insert(ApprovalRecord record);

    int update(ApprovalRecord record);

    int updateStatus(@Param("id") Long id, @Param("approverId") Long approverId,
                     @Param("status") Integer status, @Param("remark") String remark);
}
