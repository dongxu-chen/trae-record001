package com.coupon.dto;

import com.coupon.model.enums.SceneType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.io.Serializable;

@Data
public class CouponIssueRequest implements Serializable {

    private static final long serialVersionUID = 1L;

    @NotBlank(message = "用户ID不能为空")
    private String userId;

    @NotNull(message = "场景类型不能为空")
    private SceneType sceneType;
}
