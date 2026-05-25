package com.survey.model;

import lombok.Data;

@Data
public class Option {
    private String id;
    private String text;
    private Integer sortOrder;
}
