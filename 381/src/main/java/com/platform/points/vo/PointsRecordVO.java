package com.platform.points.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class PointsRecordVO {

    private Long id;

    private Long userId;

    private String orderNo;

    private Integer pointsType;

    private String pointsTypeName;

    private Integer pointsSource;

    private String pointsSourceName;

    private Integer points;

    private Integer balanceBefore;

    private Integer balanceAfter;

    private String description;

    private String remark;

    private LocalDateTime createTime;
}
