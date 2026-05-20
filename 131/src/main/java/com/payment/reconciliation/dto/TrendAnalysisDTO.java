package com.payment.reconciliation.dto;

import lombok.Data;

import java.time.LocalDate;

@Data
public class TrendAnalysisDTO {

    private String channelCode;

    private LocalDate startDate;

    private LocalDate endDate;

    private Integer groupType;
}
