package com.abtest.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class BucketAssignmentDTO {
    private String userId;
    private Long experimentId;
    private String experimentName;
    private String variantName;
    private String variantConfiguration;
    private Boolean isControl;
    private Integer bucket;
}
