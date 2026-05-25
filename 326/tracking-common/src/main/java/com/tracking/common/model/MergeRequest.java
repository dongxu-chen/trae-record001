package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MergeRequest implements Serializable {

    private static final long serialVersionUID = 1L;

    private String requestId;

    private String targetUserId;

    private List<String> sourceUserIds;

    private List<String> deviceIds;

    private String reason;

    private Double confidence;

    private Map<String, Object> evidence;

    private String status;

    private String reviewedBy;

    private Long reviewedTime;

    private String reviewComment;

    private Long createTime;

    private Long expireTime;

    private String source;
}
