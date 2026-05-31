package com.checkin.dto;

import lombok.Data;
import java.time.LocalDate;

@Data
public class RecheckDTO {
    private Long userId;
    private String periodType;
    private LocalDate checkinDate;
}
