package com.coupon.model;

import com.alibaba.fastjson2.annotation.JSONField;
import com.coupon.model.enums.CouponStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CouponDistribution implements Serializable {

    private static final long serialVersionUID = 1L;

    @JSONField(name = "distribution_id")
    private String distributionId;

    @JSONField(name = "user_id")
    private String userId;

    @JSONField(name = "coupon_id")
    private String couponId;

    @JSONField(name = "coupon_code")
    private String couponCode;

    @JSONField(name = "denomination")
    private BigDecimal denomination;

    @JSONField(name = "coupon_type")
    private Integer couponType;

    @JSONField(name = "scene_code")
    private Integer sceneCode;

    @JSONField(name = "min_order_amount")
    private BigDecimal minOrderAmount;

    @JSONField(name = "status")
    private CouponStatus status;

    @JSONField(name = "experiment_id")
    private String experimentId;

    @JSONField(name = "group_id")
    private String groupId;

    @JSONField(name = "issue_time")
    private LocalDateTime issueTime;

    @JSONField(name = "expire_time")
    private LocalDateTime expireTime;

    @JSONField(name = "use_time")
    private LocalDateTime useTime;

    @JSONField(name = "order_id")
    private String orderId;

    @JSONField(name = "order_amount")
    private BigDecimal orderAmount;

    @JSONField(name = "discount_amount")
    private BigDecimal discountAmount;

    @JSONField(name = "rl_action_index")
    private Integer rlActionIndex;

    @JSONField(name = "rl_reward")
    private Double rlReward;

    @JSONField(name = "state_vector")
    private String stateVector;

    @JSONField(name = "create_time")
    private LocalDateTime createTime;

    @JSONField(name = "update_time")
    private LocalDateTime updateTime;
}
