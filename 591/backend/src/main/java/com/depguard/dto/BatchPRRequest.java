package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class BatchPRRequest {
    private List<Long> upgradeIds;
    private boolean autoCreatePR;
}
