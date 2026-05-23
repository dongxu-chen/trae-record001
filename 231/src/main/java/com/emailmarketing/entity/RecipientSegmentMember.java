package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("recipient_segment_member")
public class RecipientSegmentMember {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long segmentId;
    private Long recipientId;
    private String email;
    private BigDecimal score;
    private LocalDateTime createdAt;
}
