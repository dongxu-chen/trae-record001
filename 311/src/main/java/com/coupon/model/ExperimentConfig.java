package com.coupon.model;

import com.alibaba.fastjson2.annotation.JSONField;
import com.coupon.model.enums.SceneType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExperimentConfig implements Serializable {

    private static final long serialVersionUID = 1L;

    @JSONField(name = "experiment_id")
    private String experimentId;

    @JSONField(name = "experiment_name")
    private String experimentName;

    @JSONField(name = "description")
    private String description;

    @JSONField(name = "scene_type")
    private SceneType sceneType;

    @JSONField(name = "status")
    private Integer status;

    @JSONField(name = "total_traffic_percent")
    private Integer totalTrafficPercent;

    @JSONField(name = "groups")
    private List<ExperimentGroup> groups;

    @JSONField(name = "start_time")
    private LocalDateTime startTime;

    @JSONField(name = "end_time")
    private LocalDateTime endTime;

    @JSONField(name = "create_time")
    private LocalDateTime createTime;

    @JSONField(name = "update_time")
    private LocalDateTime updateTime;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ExperimentGroup implements Serializable {
        private static final long serialVersionUID = 1L;

        @JSONField(name = "group_id")
        private String groupId;

        @JSONField(name = "group_name")
        private String groupName;

        @JSONField(name = "group_type")
        private String groupType;

        @JSONField(name = "traffic_percent")
        private Integer trafficPercent;

        @JSONField(name = "is_rl_enabled")
        private Boolean isRlEnabled;

        @JSONField(name = "fixed_coupon_id")
        private String fixedCouponId;

        @JSONField(name = "fixed_denomination")
        private BigDecimal fixedDenomination;

        @JSONField(name = "fixed_coupon_type")
        private Integer fixedCouponType;

        @JSONField(name = "min_order_amount")
        private BigDecimal minOrderAmount;
    }

    public boolean isActive() {
        LocalDateTime now = LocalDateTime.now();
        return status == 1
                && now.isAfter(startTime)
                && now.isBefore(endTime);
    }
}
