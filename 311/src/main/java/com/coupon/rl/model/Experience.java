package com.coupon.rl.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Experience implements Serializable {

    private static final long serialVersionUID = 1L;

    private double[] state;

    private int action;

    private double reward;

    private double[] nextState;

    private boolean done;

    private long timestamp;

    private String userId;
}
