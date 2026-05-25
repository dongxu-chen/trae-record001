package com.coupon.rl.model;

import com.coupon.model.enums.CouponType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CouponAction implements Serializable {

    private static final long serialVersionUID = 1L;

    private int actionIndex;

    private CouponType couponType;

    private BigDecimal denomination;

    private BigDecimal minOrderAmount;

    private int validDays;

    public static CouponAction fromIndex(int actionIndex) {
        int typeIndex = actionIndex / 4;
        int denominationIndex = actionIndex % 4;

        CouponType[] types = CouponType.values();
        CouponType type = types[typeIndex % types.length];

        BigDecimal[] denominations = {
                new BigDecimal("5"),
                new BigDecimal("10"),
                new BigDecimal("20"),
                new BigDecimal("50")
        };

        BigDecimal denomination = denominations[denominationIndex];

        BigDecimal minOrderAmount = denomination.multiply(new BigDecimal("3"));

        return CouponAction.builder()
                .actionIndex(actionIndex)
                .couponType(type)
                .denomination(denomination)
                .minOrderAmount(minOrderAmount)
                .validDays(7)
                .build();
    }

    public static int getTotalActions() {
        return CouponType.values().length * 4;
    }
}
