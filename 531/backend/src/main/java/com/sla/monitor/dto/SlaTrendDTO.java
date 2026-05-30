package com.sla.monitor.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class SlaTrendDTO {
    private LocalDateTime timestamp;
    private Double value;
}
