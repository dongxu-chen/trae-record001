package com.payment.reconciliation.dto;

import lombok.Data;

import java.time.LocalDate;

@Data
public class ReportQueryDTO {

    private String channelCode;

    private LocalDate startDate;

    private LocalDate endDate;

    private Integer status;
}
