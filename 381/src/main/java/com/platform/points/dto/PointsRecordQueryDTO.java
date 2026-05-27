package com.platform.points.dto;

import lombok.Data;

import javax.validation.constraints.NotNull;

@Data
public class PointsRecordQueryDTO {

    private Long userId;

    private Integer pointsType;

    private Integer pointsSource;

    private String startTime;

    private String endTime;

    @NotNull(message = "页码不能为空")
    private Integer pageNum = 1;

    @NotNull(message = "每页条数不能为空")
    private Integer pageSize = 10;
}
