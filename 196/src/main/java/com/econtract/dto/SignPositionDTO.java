package com.econtract.dto;

import lombok.Data;

@Data
public class SignPositionDTO {

    private String positionKey;

    private Integer pageNum;

    private Float x;

    private Float y;

    private Float width;

    private Float height;

    private Integer signerOrder;
}
