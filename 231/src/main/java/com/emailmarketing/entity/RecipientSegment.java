package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("recipient_segment")
public class RecipientSegment extends BaseEntity {
    private String segmentName;
    private String segmentDesc;
    private Integer segmentType;
    private String criteria;
    private Integer recipientCount;
    private Integer status;
    private Integer autoRefresh;
    private LocalDateTime lastRefreshTime;
}
