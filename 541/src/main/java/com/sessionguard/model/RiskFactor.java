package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RiskFactor implements Serializable {

    private static final long serialVersionUID = 1L;

    private String category;

    private String name;

    private String description;

    private int weight;

    private int score;

    private String detail;
}
